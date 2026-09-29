import fitz
from fastapi.testclient import TestClient
from app.main import app
from app.deps.auth import AuthenticatedUser, get_current_user

from supabase import create_client
from app.core.config import settings

# Retrieve or create real test user from Supabase Auth
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


def generate_sample_kfs_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "KEY FACT STATEMENT (KFS) - PERSONAL LOAN\n\n"
        "Lender: Apex Financial Bank\n"
        "Borrower: Test Borrower\n"
        "Loan Amount: Rs. 1,00,000\n"
        "Interest Rate: 13.5% p.a.\n"
        "Tenure: 24 Months\n"
        "Processing Fee: Rs. 1,500\n"
        "Prepayment: Zero foreclosure charges after 6 months.\n"
    )
    page.insert_text((50, 72), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_loan_intake_and_manual_terms_pipeline():
    # 1. Create a Loan
    create_resp = client.post(
        "/api/v1/loans",
        json={
            "loan_name": "Personal Loan Offer A",
            "lender_name": "Apex Financial Bank",
        },
    )
    assert create_resp.status_code == 201
    loan_data = create_resp.json()
    loan_id = loan_data["id"]
    assert loan_data["loan_name"] == "Personal Loan Offer A"
    assert loan_data["user_id"] == TEST_USER_ID

    # 2. Enter Manual Terms
    terms_payload = {
        "principal": 100000.0,
        "disclosed_rate": 13.5,
        "tenure_months": 24,
        "fees": 1500.0,
    }
    terms_resp = client.post(f"/api/v1/loans/{loan_id}/terms", json=terms_payload)
    assert terms_resp.status_code == 201
    terms_data = terms_resp.json()
    assert terms_data["principal"] == 100000.0
    assert terms_data["tenure_months"] == 24

    # 3. Retrieve Manual Terms
    get_terms_resp = client.get(f"/api/v1/loans/{loan_id}/terms")
    assert get_terms_resp.status_code == 200
    assert get_terms_resp.json()["principal"] == 100000.0

    # 4. Upload KFS PDF Document
    kfs_bytes = generate_sample_kfs_pdf()
    files = {"file": ("kfs_document.pdf", kfs_bytes, "application/pdf")}
    data = {"doc_type": "kfs"}

    upload_resp = client.post(
        f"/api/v1/loans/{loan_id}/documents/upload", files=files, data=data
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    doc_id = upload_data["doc_id"]
    assert upload_data["doc_type"] == "kfs"
    assert upload_data["version"] >= 1
    assert len(upload_data["extracted_fields"]) >= 4

    # Verify structured fields
    fields_resp = client.get(f"/api/v1/loans/{loan_id}/documents/{doc_id}/fields")
    assert fields_resp.status_code == 200
    fields_list = fields_resp.json()
    field_names = [f["field_name"] for f in fields_list]
    assert "principal" in field_names
    assert "disclosed_rate" in field_names
    assert "tenure_months" in field_names

    # 5. Verify Automatic Trigger of Phase 2 Recompute & Phase 3 Consistency Check (STATUS.md line 31, IMPLEMENTATION_PLAN.md line 89)
    claims_res = (
        supabase_admin.table("claims").select("*").eq("loan_id", loan_id).execute()
    )
    claim_sources = [c["source_module"] for c in claims_res.data]
    assert (
        "recompute" in claim_sources
    ), "Expected automatic APR recompute claim upon KFS upload"
    assert (
        "consistency" in claim_sources
    ), "Expected automatic consistency check claim upon KFS upload"

    cc_res = (
        supabase_admin.table("consistency_checks")
        .select("*")
        .eq("loan_id", loan_id)
        .execute()
    )
    assert (
        len(cc_res.data) >= 4
    ), "Expected automatic consistency check rows upon KFS upload"
