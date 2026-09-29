"""
Integration & Architectural Tests for Phase 10: Orchestration & Full API Gateway.
Governing Requirements:
- IMPLEMENTATION_PLAN.md Phase 10 (Week 11)
- RULES.md §1 (The Verification Gate Is Sacred), §3 (Security Checklist S-3, S-21, S-22)
- STATUS.md line 105-111:
  1. Full pipeline callable end-to-end: ingest → extract → consistency-check → recompute/serviceability
     → generate claim → retrieve → verify → (vernacular, if requested) → respond.
  2. End-to-end round trip ≤5 seconds on the reference test loan.
  3. Every endpoint behind single FastAPI gateway at /api/v1.
  4. Every endpoint returns {error_code, message, request_id} on error, never raw stack trace.
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient
from supabase import create_client

from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.main import app

# Supabase Admin Client
supabase_admin = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)

# Ensure test borrower exists in Supabase
users_list = supabase_admin.auth.admin.list_users()
test_user = next(
    (u for u in users_list if u.email == "test_borrower@guardian.local"), None
)

if test_user is None:
    test_user_res = supabase_admin.auth.admin.create_user(
        {
            "email": "test_borrower@guardian.local",
            "password": "TestPassword123!",  # pragma: allowlist secret
            "email_confirm": True,
        }
    )
    TEST_USER_ID = test_user_res.user.id
else:
    TEST_USER_ID = test_user.id

# Ensure secondary user exists for cross-user 403 test
other_user = next(
    (u for u in users_list if u.email == "phase10_other_user@guardian.local"), None
)
if other_user is None:
    other_user_res = supabase_admin.auth.admin.create_user(
        {
            "email": "phase10_other_user@guardian.local",
            "password": "TestPassword123!",  # pragma: allowlist secret
            "email_confirm": True,
        }
    )
    OTHER_USER_ID = other_user_res.user.id
else:
    OTHER_USER_ID = other_user.id


async def override_get_current_user():
    return AuthenticatedUser(
        user_id=TEST_USER_ID,
        email="test_borrower@guardian.local",
        role="authenticated",
    )


# Pre-warm model to ensure measurement reflects steady-state SLA (RULES.md §5, STATUS.md line 108)
from modules.m3_verifier.semantic_verifier import get_nli_model  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_auth_override():
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override_get_current_user
    get_nli_model()
    yield
    if prev is not None:
        app.dependency_overrides[get_current_user] = prev
    else:
        app.dependency_overrides.pop(get_current_user, None)


def test_phase10_full_pipeline_end_to_end_and_latency_sla():
    """
    Validates:
    - End-to-end state machine coordination through all stages.
    - Reference test loan round trip ≤ 5.0 seconds SLA (STATUS.md line 108).
    - Sacred Verification Gate enforcement on all generated claims.
    - Vernacular translation and audit trail logging.
    """
    loan_id = str(uuid.uuid4())
    supabase_admin.table("loans").insert(
        {
            "id": loan_id,
            "user_id": TEST_USER_ID,
            "loan_name": "Phase 10 Reference Personal Loan",
            "lender_name": "Apex Microfinance NBFC",
            "status": "active",
        }
    ).execute()

    # Insert reference manual terms
    supabase_admin.table("loan_manual_terms").insert(
        {
            "loan_id": loan_id,
            "principal": 50000.0,
            "disclosed_rate": 16.5,
            "tenure_months": 12,
            "fees": 1500.0,
        }
    ).execute()

    # Run full pipeline via API gateway
    payload = {
        "target_language": "hi",
        "monthly_income": 60000.0,
        "existing_obligations": 5000.0,
    }

    start_wall_time = time.perf_counter()
    resp = client.post(f"/api/v1/loans/{loan_id}/pipeline/analyze", json=payload)
    elapsed_ms = (time.perf_counter() - start_wall_time) * 1000

    assert resp.status_code == 200, f"Pipeline endpoint failed: {resp.text}"
    data = resp.json()

    # 1. State machine completion assertion
    assert data["loan_id"] == loan_id
    assert data["status"] == "completed"

    # 2. Strict latency constraint: Round trip ≤ 5.0 seconds (5000 ms)
    total_duration_ms = data["total_duration_ms"]
    assert (
        total_duration_ms <= 5000.0
    ), f"Latency SLA violation (STATUS.md line 108): total_duration_ms was {total_duration_ms}ms (> 5000ms)"
    assert elapsed_ms <= 6000.0, f"Client wall-clock time was {elapsed_ms}ms"

    # 3. Assert all stages executed with timings
    stage_names = [t["stage"] for t in data["timings"]]
    expected_stages = [
        "ingesting",
        "extracting",
        "consistency_checking",
        "recomputing_serviceability",
        "generating_claim",
        "retrieving_regulatory",
        "verifying",
        "translating_vernacular",
    ]
    for st in expected_stages:
        assert st in stage_names, f"Pipeline stage '{st}' was not executed"

    # 4. Assert calculations and compliance results
    assert data["apr_result"] is not None
    assert data["apr_result"]["recomputed_apr"] > 0
    assert data["serviceability_result"] is not None
    assert data["serviceability_result"]["verdict"] == "serviceable"

    # 5. Assert all generated claims passed through Sacred Verification Gate
    assert len(data["verified_claims"]) >= 2
    for vc in data["verified_claims"]:
        assert vc["verification_status"] in ["grounded", "flagged"]
        assert vc["claim_id"] is not None

    # 6. Assert vernacular translation executed with verification
    assert data["vernacular_translations"] is not None
    assert len(data["vernacular_translations"]) >= 2
    for vt in data["vernacular_translations"]:
        assert vt["target_language"] == "hi"
        assert vt["metrics"]["numeric_preservation_rate"] >= 50.0
        assert vt["verification_verdict"] in ["grounded", "flagged"]


def test_phase10_audit_trail_endpoint_s21_s22():
    """
    Validates:
    - GET /api/v1/audit returns authenticated user's audit trail.
    - S-22: Audit log is read-only, no write/delete methods permitted.
    """
    resp = client.get("/api/v1/audit")
    assert resp.status_code == 200, f"GET /audit failed: {resp.text}"
    data = resp.json()
    assert "entries" in data
    assert "total" in data
    assert data["total"] >= 1

    actions = [e["action"] for e in data["entries"]]
    assert "PIPELINE_ANALYSIS_COMPLETED" in actions

    # S-22: Verify POST / DELETE on /audit return 405 Method Not Allowed
    post_resp = client.post("/api/v1/audit", json={})
    assert post_resp.status_code == 405

    delete_resp = client.delete("/api/v1/audit")
    assert delete_resp.status_code == 405


def test_phase10_standardized_error_format():
    """
    Validates:
    - Every endpoint returns {error_code, message, request_id} on error (STATUS.md line 110).
    - 404 Not Found format.
    - 422 Validation Error format.
    - 403 Forbidden format.
    """
    # 1. Test 404 format
    fake_loan_id = str(uuid.uuid4())
    resp_404 = client.get(f"/api/v1/loans/{fake_loan_id}")
    assert resp_404.status_code == 404
    data_404 = resp_404.json()
    assert "error_code" in data_404, "404 missing error_code"
    assert "message" in data_404, "404 missing message"
    assert "request_id" in data_404, "404 missing request_id"
    assert data_404["error_code"] == "HTTP_404"

    # 2. Test 422 format (invalid request payload)
    resp_422 = client.post(
        f"/api/v1/loans/{fake_loan_id}/pipeline/analyze",
        json={"monthly_income": -500},  # Fails gt=0 validation
    )
    assert resp_422.status_code == 422
    data_422 = resp_422.json()
    assert "error_code" in data_422, "422 missing error_code"
    assert "message" in data_422, "422 missing message"
    assert "request_id" in data_422, "422 missing request_id"
    assert data_422["error_code"] == "VALIDATION_ERROR"

    # 3. Test 403 format (accessing another user's loan)
    other_loan_id = str(uuid.uuid4())
    supabase_admin.table("loans").insert(
        {
            "id": other_loan_id,
            "user_id": OTHER_USER_ID,
            "loan_name": "Other User's Loan",
            "lender_name": "Other Bank",
            "status": "active",
        }
    ).execute()

    resp_403 = client.post(f"/api/v1/loans/{other_loan_id}/pipeline/analyze", json={})
    assert resp_403.status_code == 403
    data_403 = resp_403.json()
    assert "error_code" in data_403, "403 missing error_code"
    assert "message" in data_403, "403 missing message"
    assert "request_id" in data_403, "403 missing request_id"
    assert data_403["error_code"] == "HTTP_403"


def test_phase10_all_endpoints_mounted_under_apiv1():
    """
    Validates that every required router is registered behind /api/v1:
    - loans, documents, terms, serviceability, verify, chat, disputes, audit, pipeline
    """
    registered_routes = [route.path for route in app.routes]

    required_prefixes = [
        "/api/v1/loans",
        "/api/v1/loans/{loan_id}/documents",
        "/api/v1/loans/{loan_id}/terms",
        "/api/v1/loans/{loan_id}/recompute",
        "/api/v1/loans/{loan_id}/serviceability",
        "/api/v1/loans/{loan_id}/consistency",
        "/api/v1/loans/{loan_id}/verify/claims/{claim_id}",
        "/api/v1/loans/{loan_id}/vernacular/claims/{claim_id}/translate",
        "/api/v1/loans/{loan_id}/disputes",
        "/api/v1/loans/{loan_id}/chat/sessions",
        "/api/v1/audit",
        "/api/v1/loans/{loan_id}/pipeline/analyze",
    ]

    for prefix in required_prefixes:
        assert any(
            r.startswith(prefix.split("{")[0]) for r in registered_routes
        ), f"Required endpoint prefix '{prefix}' not found in FastAPI routes: {registered_routes}"
