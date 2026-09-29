"""
Training and evaluation dataset for Module 5 (Grievance Classification).
Grounded in National Consumer Helpline complaint patterns and RBI Digital Lending Directions.
"""

from typing import Dict, List, Tuple

CATEGORY_METADATA: Dict[str, Dict[str, str]] = {
    "excessive_charges_and_hidden_fees": {
        "label": "Excessive Interest & Undisclosed Fees",
        "rbi_clause": "Clause 3.3 (Prohibition of undisclosed charges) & Clause 5.1 (Non-capitalization of penal charges)",
    },
    "recovery_harassment_and_privacy": {
        "label": "Recovery Harassment & Privacy Breach",
        "rbi_clause": "Clause 5.4 (Code of conduct for recovery) & Clause 7 (Prohibition of accessing phone contact lists)",
    },
    "unauthorized_disbursal_or_credit_limit": {
        "label": "Unauthorized Disbursal / Limit Increase",
        "rbi_clause": "Clause 4.1 (Direct account-to-account transfer) & Clause 4.2 (Prohibition of automatic credit limit hike)",
    },
    "transparency_and_kfs_violation": {
        "label": "KFS Non-Issuance & Transparency Violations",
        "rbi_clause": "Clause 3.1 (Mandatory KFS issuance) & Clause 3.2 (Mandatory cooling-off / look-up exit period)",
    },
    "repayment_and_noc_delay": {
        "label": "Repayment Accounting Delay & Bureau Reporting",
        "rbi_clause": "Clause 5.2 (Prohibition of prepayment penalty on floating loans) & Credit Information Companies (CIC) Regulations",
    },
    "general_service_deficiency": {
        "label": "Grievance Redressal Unresponsiveness & TAT Breach",
        "rbi_clause": "Clause 6.1 (Mandatory appointment of Nodal Grievance Redressal Officer with max 30-day TAT)",
    },
}

TRAINING_DATA: List[Tuple[str, str]] = [
    # 1. excessive_charges_and_hidden_fees
    (
        "The lender deducted 15% upfront processing fees and added hidden insurance charges never mentioned in the loan offer.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "My loan agreement said 14% interest rate but they are charging effective APR of 42% with compounding daily penalties.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "The lending app is charging penal interest on top of overdue penal charges, which is illegal compounding.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "They deducted an unexpected administrative fee of Rs 3,500 from my disbursement amount without prior disclosure.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "Undisclosed platform convenience fee of Rs 1,200 charged on every monthly EMI payment.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "The NBFC charged me exorbitant hidden processing charges of 8% which were not shown anywhere in the sanctioned terms.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "Compound interest is being calculated on penal charges during overdue periods, inflating my outstanding balance.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "Usurious rate of interest exceeding 50% p.a. charged through hidden recurring technology maintenance fees.",
        "excessive_charges_and_hidden_fees",
    ),
    # 2. recovery_harassment_and_privacy
    (
        "Collection agents accessed my mobile contact list and are calling my relatives and colleagues threatening them.",
        "recovery_harassment_and_privacy",
    ),
    (
        "Recovery agents arrived at my workplace and shouted abusive language in front of my manager and coworkers.",
        "recovery_harassment_and_privacy",
    ),
    (
        "I am getting continuous threatening WhatsApp messages and morphed pictures from the recovery team at 2 AM.",
        "recovery_harassment_and_privacy",
    ),
    (
        "The lending company shared my confidential financial details with third-party telecallers without my consent.",
        "recovery_harassment_and_privacy",
    ),
    (
        "Recovery agents are calling my elderly parents repeatedly and threatening police action for an overdue EMI.",
        "recovery_harassment_and_privacy",
    ),
    (
        "The app secretly scraped my phone contacts and photo gallery permissions during installation and is blackmailing me.",
        "recovery_harassment_and_privacy",
    ),
    (
        "Harassing phone calls from unknown recovery numbers outside permitted business hours, including late night calls.",
        "recovery_harassment_and_privacy",
    ),
    (
        "Abusive language used by field recovery agent demanding immediate cash payment at my home address.",
        "recovery_harassment_and_privacy",
    ),
    # 3. unauthorized_disbursal_or_credit_limit
    (
        "The loan amount was transferred to a third party wallet account instead of my verified bank account.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "The digital lending app increased my credit line from Rs 20,000 to Rs 80,000 without my consent or application.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "An unauthorized instant loan was booked and disbursed under my PAN card without my knowledge or OTP confirmation.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "Disbursement was routed through an unapproved pool account of the lending service provider instead of directly from the bank.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "Automatic credit limit enhancement applied to my account despite me explicitly rejecting the notification.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "The LSP disbursed funds to a merchant gateway pool instead of transferring directly to borrower savings account.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "I discovered a loan disbursed in my name that I never applied for, with funds sent to an unknown bank account.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "Credit limit hiked automatically and fees charged for limit enhancement without recorded consent.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    # 4. transparency_and_kfs_violation
    (
        "The lender never provided me a Key Fact Statement (KFS) before forcing me to sign the agreement.",
        "transparency_and_kfs_violation",
    ),
    (
        "I requested to cancel the loan within the 3-day cooling-off look-up period, but customer care refused my exit.",
        "transparency_and_kfs_violation",
    ),
    (
        "The KFS format does not disclose the Annual Percentage Rate (APR) or the recovery mechanism details.",
        "transparency_and_kfs_violation",
    ),
    (
        "Lender refused to accept prepayment during the look-up period and demanded heavy foreclosure fees.",
        "transparency_and_kfs_violation",
    ),
    (
        "No sanction letter or KFS was shared with me, only an SMS with a payment link was sent.",
        "transparency_and_kfs_violation",
    ),
    (
        "Cooling-off exit period was denied by the fintech platform claiming that their digital loans do not have cancellation rights.",
        "transparency_and_kfs_violation",
    ),
    (
        "The computation of APR was concealed and omitted from the loan summary sheet provided in the app.",
        "transparency_and_kfs_violation",
    ),
    (
        "Agreement terms differed significantly from the initial digital advertisement and no KFS was delivered to email.",
        "transparency_and_kfs_violation",
    ),
    # 5. repayment_and_noc_delay
    (
        "I paid off my complete loan balance 3 months ago but the bank has still not updated CIBIL and my score dropped.",
        "repayment_and_noc_delay",
    ),
    (
        "The NBFC is refusing to issue a No Objection Certificate (NOC) and No Due Certificate despite full loan clearance.",
        "repayment_and_noc_delay",
    ),
    (
        "They charged a 4% prepayment penalty on my floating-rate personal loan, which violates RBI directions.",
        "repayment_and_noc_delay",
    ),
    (
        "My EMI was successfully debited from my bank account but the loan app still shows the installment as unpaid.",
        "repayment_and_noc_delay",
    ),
    (
        "Delay of over 60 days in releasing collateral documents and providing No Due Certificate after full foreclosure.",
        "repayment_and_noc_delay",
    ),
    (
        "Credit bureau Experian shows active overdue status even though I hold the final settlement payment receipt.",
        "repayment_and_noc_delay",
    ),
    (
        "Illegal foreclosure charges and prepayment penalties levied on floating rate individual loan.",
        "repayment_and_noc_delay",
    ),
    (
        "Payment made through UPI was credited to lender but account ledger continues to show overdue status with penalties.",
        "repayment_and_noc_delay",
    ),
    # 6. general_service_deficiency
    (
        "Customer support email and helpline numbers are continuously unreachable and tickets are closed without response.",
        "general_service_deficiency",
    ),
    (
        "I filed a formal complaint with the grievance officer 45 days ago but have received no acknowledgement or reply.",
        "general_service_deficiency",
    ),
    (
        "The lender has not published the name or contact details of their Principal Nodal Grievance Redressal Officer.",
        "general_service_deficiency",
    ),
    (
        "Grievance turnaround time has exceeded the mandatory 30-day limit without any resolution or explanation.",
        "general_service_deficiency",
    ),
    (
        "App customer support chat is purely an unhelpful automated bot with no option to connect to a human agent.",
        "general_service_deficiency",
    ),
    (
        "Grievance redressal mechanism is completely missing on the lending website, preventing formal dispute filing.",
        "general_service_deficiency",
    ),
    (
        "Nodal officer phone number listed on the portal is permanently disconnected and emails bounce back.",
        "general_service_deficiency",
    ),
    (
        "No resolution provided after multiple escalated tickets; dispute pending for over two months.",
        "general_service_deficiency",
    ),
]

TEST_DATA: List[Tuple[str, str]] = [
    (
        "Hidden insurance premium of Rs 5,000 added into my loan without asking me.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "Daily penal fee of Rs 200 is being capitalized into principal every week.",
        "excessive_charges_and_hidden_fees",
    ),
    (
        "Recovery agents sent threatening messages to my wife and brother.",
        "recovery_harassment_and_privacy",
    ),
    (
        "Agent showed up at my home threatening to seize my furniture without any legal order.",
        "recovery_harassment_and_privacy",
    ),
    (
        "My credit limit was doubled overnight without my permission and limit fees charged.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "Money was disbursed to a pass-through account instead of direct transfer to my SBI account.",
        "unauthorized_disbursal_or_credit_limit",
    ),
    (
        "The company refuses to give me a Key Fact Statement (KFS) detailing the breakdown of APR.",
        "transparency_and_kfs_violation",
    ),
    (
        "I exercised my right to exit during the look-up period within 48 hours but lender rejected cancellation.",
        "transparency_and_kfs_violation",
    ),
    (
        "Loan is fully cleared but NBFC has not updated CIBIL records or issued NOC for past two months.",
        "repayment_and_noc_delay",
    ),
    (
        "Foreclosure penalty of 3% charged on floating rate loan closure.",
        "repayment_and_noc_delay",
    ),
    (
        "No response from Grievance Officer after 35 days of submitting complaint.",
        "general_service_deficiency",
    ),
    (
        "The fintech app has no customer support contact details or grievance redressal mechanism.",
        "general_service_deficiency",
    ),
]
