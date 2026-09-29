from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from supabase import create_client
from app.core.config import settings
from app.deps.auth import AuthenticatedUser, get_current_user
from app.main import app

supabase_admin = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)
users_list = supabase_admin.auth.admin.list_users()
test_user = next(
    (u for u in users_list if u.email == "test_borrower@guardian.local"), None
)

if test_user is None:
    test_user_res = supabase_admin.auth.admin.create_user(
        {
            "email": "test_borrower@guardian.local",
            "password": "TestPassword123!",
            "email_confirm": True,
        }
    )
    TEST_USER_ID = test_user_res.user.id
else:
    TEST_USER_ID = test_user.id


async def override_get_current_user():
    return AuthenticatedUser(
        user_id=TEST_USER_ID,
        email="test_borrower@guardian.local",
        role="authenticated",
    )


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


def test_consistency_check_pipeline():
    # Step 1: Create Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Phase 3 Consistency Loan",
            "lender_name": "Consistency Bank",
        },
    )
    assert create_resp.status_code == 201
    loan_id = create_resp.json()["id"]

    # Step 2: Post Manual Terms
    terms_payload = {
        "principal": 100000.0,
        "disclosed_rate": 12.0,
        "tenure_months": 12,
        "fees": 1500.0,
    }
    terms_resp = client.post(f"/api/v1/loans/{loan_id}/terms", json=terms_payload)
    assert terms_resp.status_code == 201

    # Step 3: Insert T&C Document and Extracted Fields in Supabase
    tnc_doc_id = str(uuid4())
    supabase_admin.table("loan_documents").insert(
        {
            "doc_id": tnc_doc_id,
            "loan_id": loan_id,
            "doc_type": "tnc",
            "storage_path": f"{loan_id}/tnc_v1.pdf",
            "version": 1,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    tnc_fields = [
        ("principal", 100000.0),
        ("disclosed_rate", 12.0),
        ("tenure_months", 12),
        ("processing_fee", 1500.0),
        (
            "prepayment_clause",
            "Nil foreclosure charges or prepayment penalty applicable on personal loans.",
        ),
    ]
    for fname, val in tnc_fields:
        supabase_admin.table("extracted_fields").insert(
            {
                "doc_id": tnc_doc_id,
                "field_name": fname,
                "extracted_value": {"value": val},
                "confidence": 0.95,
                "extraction_method": "test_fixture",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

    # Step 4: Insert KFS Document and Extracted Fields (Matching initially)
    kfs_doc_id = str(uuid4())
    supabase_admin.table("loan_documents").insert(
        {
            "doc_id": kfs_doc_id,
            "loan_id": loan_id,
            "doc_type": "kfs",
            "storage_path": f"{loan_id}/kfs_v1.pdf",
            "version": 1,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    kfs_fields = [
        ("principal", 100000.0),
        ("disclosed_rate", 12.0),
        ("tenure_months", 12),
        ("processing_fee", 1500.0),
        ("prepayment_clause", "Nil prepayment charges during entire loan period."),
    ]
    for fname, val in kfs_fields:
        supabase_admin.table("extracted_fields").insert(
            {
                "doc_id": kfs_doc_id,
                "field_name": fname,
                "extracted_value": {"value": val},
                "confidence": 0.98,
                "extraction_method": "test_fixture",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

    # Step 5: Execute Consistency Check (Clean Match Test)
    resp = client.post(f"/api/v1/loans/{loan_id}/consistency")
    assert resp.status_code == 200
    data = resp.json()

    assert data["loan_id"] == loan_id
    assert data["overall_status"] == "match"
    assert data["mismatch_count"] == 0
    assert data["match_count"] == 5
    assert not data["requires_human_review"]
    claim_id = data["claim_id"]
    assert claim_id is not None

    # Verify rows in Supabase consistency_checks table
    cc_res = (
        supabase_admin.table("consistency_checks")
        .select("*")
        .eq("loan_id", loan_id)
        .execute()
    )
    assert len(cc_res.data) >= 5
    for row in cc_res.data:
        assert row["match_status"] in ("match", "mismatch", "missing")

    # Verify claim in Supabase claims table (RULES.md §1.1, §1.8)
    claim_res = (
        supabase_admin.table("claims").select("*").eq("claim_id", claim_id).execute()
    )
    assert len(claim_res.data) == 1
    assert claim_res.data[0]["source_module"] == "consistency"
    assert claim_res.data[0]["verification_status"] == "pending"

    # Step 6: Inject Mismatch in KFS (Fees & Prepayment Contradiction)
    kfs_doc_id_v2 = str(uuid4())
    supabase_admin.table("loan_documents").insert(
        {
            "doc_id": kfs_doc_id_v2,
            "loan_id": loan_id,
            "doc_type": "kfs",
            "storage_path": f"{loan_id}/kfs_v2.pdf",
            "version": 2,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    kfs_mismatched_fields = [
        ("principal", 100000.0),
        ("disclosed_rate", 12.0),
        ("tenure_months", 12),
        ("processing_fee", 5000.0),  # Injected fee mismatch (5000 vs 1500)
        (
            "prepayment_clause",
            "Prepayment penalty of 3.5% plus GST applicable on outstanding loan amount.",
        ),  # Injected contradiction
    ]
    for fname, val in kfs_mismatched_fields:
        supabase_admin.table("extracted_fields").insert(
            {
                "doc_id": kfs_doc_id_v2,
                "field_name": fname,
                "extracted_value": {"value": val},
                "confidence": 0.98,
                "extraction_method": "test_fixture",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

    # Step 7: Run Consistency Check on Mismatched Version
    resp_mismatch = client.post(f"/api/v1/loans/{loan_id}/consistency")
    assert resp_mismatch.status_code == 200
    data_mismatch = resp_mismatch.json()

    assert data_mismatch["overall_status"] == "mismatch"
    assert data_mismatch["mismatch_count"] == 2
    assert data_mismatch["requires_human_review"] is True

    mismatched_field_names = [
        c["field_name"]
        for c in data_mismatch["checks"]
        if c["match_status"] == "mismatch"
    ]
    assert "fees" in mismatched_field_names
    assert "prepayment_clause" in mismatched_field_names
