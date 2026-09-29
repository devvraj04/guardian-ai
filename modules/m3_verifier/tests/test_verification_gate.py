import re
from pathlib import Path
from uuid import uuid4
from supabase import create_client

from app.core.config import settings
from app.orchestration.pipeline import verify_and_resolve_claim
from app.schemas.claim import Claim

supabase_admin = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
)


def test_no_verification_bypass_flags():
    """
    Security Invariant Test (RULES.md §1.2, S-18):
    There is NO debug flag, feature flag, env var, admin override,
    or 'trusted source' shortcut that skips verification in any route or pipeline.
    """
    root_dir = Path(__file__).resolve().parents[3]
    dirs_to_scan = [root_dir / "app", root_dir / "modules"]

    # Forbidden patterns per RULES.md §1.2
    forbidden_patterns = [
        re.compile(
            r"\b(?:skip_verif|bypass_verification|skip_verification|TRUSTED_SOURCE)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\bverify_claim\s*=\s*False\b", re.IGNORECASE),
    ]

    violations = []
    for d in dirs_to_scan:
        for py_file in d.rglob("*.py"):
            if "tests" in py_file.parts:
                continue
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                for pattern in forbidden_patterns:
                    matches = pattern.findall(content)
                    if matches:
                        violations.append((str(py_file.relative_to(root_dir)), matches))

    assert (
        len(violations) == 0
    ), f"Critical Security Violation (RULES.md §1.2, S-18): Verification bypass shortcut detected in: {violations}"


def test_sacred_choke_point_enforcement():
    """
    Architectural Invariant Test (RULES.md §1.1, S-17):
    No Claim object may reach a user-facing response without a corresponding
    row in verification_results, enforced by verify_and_resolve_claim().
    """
    users_list = supabase_admin.auth.admin.list_users()
    test_user = next(
        (u for u in users_list if u.email == "test_borrower@guardian.local"), None
    )
    if test_user:
        test_user_id = test_user.id
    else:
        test_user_res = supabase_admin.auth.admin.create_user(
            {
                "email": "test_borrower@guardian.local",
                "password": "TestPassword123!",  # pragma: allowlist secret
                "email_confirm": True,
            }
        )
        test_user_id = test_user_res.user.id

    # Create real loan record in public.loans to satisfy foreign key constraint
    loan_record = (
        supabase_admin.table("loans")
        .insert(
            {
                "user_id": test_user_id,
                "loan_name": "Gate Invariant Test Loan",
                "lender_name": "Test Bank",
                "status": "intake",
            }
        )
        .execute()
    )
    test_loan_id = loan_record.data[0]["id"]

    try:
        # Ingest a deliberately wrong/adversarial claim into Supabase claims table
        claim_id = str(uuid4())
        wrong_claim = Claim(
            claim_id=claim_id,
            source_module="recompute",
            user_id=test_user_id,
            loan_id=test_loan_id,
            claim_text="For a principal of ₹100,000 at 12.00% rate, the monthly EMI is ₹1,000.00.",
            supporting_figures={
                "principal": 100000.0,
                "disclosed_rate": 12.0,
                "tenure_months": 12,
                "fees": 2000.0,
            },
            source_record_id=test_loan_id,
        )

        supabase_admin.table("claims").insert(
            {
                "claim_id": wrong_claim.claim_id,
                "source_module": wrong_claim.source_module,
                "user_id": wrong_claim.user_id,
                "loan_id": wrong_claim.loan_id,
                "claim_text": wrong_claim.claim_text,
                "supporting_figures": wrong_claim.supporting_figures,
                "source_record_id": wrong_claim.source_record_id,
                "generated_at": wrong_claim.generated_at.isoformat(),
                "verification_status": "pending",
            }
        ).execute()

        # Route through Sacred Gate Choke Point
        response = verify_and_resolve_claim(
            claim_id=claim_id,
            user_id=test_user_id,
            loan_id=test_loan_id,
            supabase_client=supabase_admin,
        )

        # Invariant: Claim was unverified; must now have a row in verification_results
        verif_row = (
            supabase_admin.table("verification_results")
            .select("*")
            .eq("claim_id", claim_id)
            .execute()
        )
        assert (
            len(verif_row.data) == 1
        ), "Sacred Gate failed to record verification_results row"

        # Invariant: Flagged claim CANNOT be safe to present to user
        assert response.verification_status == "flagged"
        assert response.is_safe_to_present is False
        assert response.warning_message is not None
        assert "failed dual groundedness verification" in response.warning_message

    finally:
        # Cleanup test loan (cascades to claims and verification_results)
        supabase_admin.table("loans").delete().eq("id", test_loan_id).execute()
