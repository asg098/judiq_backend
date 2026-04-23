import logging
logger = logging.getLogger(__name__)
def normalize_input(data):
    """
    Enhanced normalizer - extracts ALL possible fields from various input formats
    Handles both camelCase and snake_case field names
    """
    return {
        # Core identifiers
        "case_id": data.get("case_id", data.get("caseId", "API_CASE")),
        "user_id": data.get("user_id", data.get("userId", "ANONYMOUS")),
        
        # Four pillars (boolean flags)
        "cheque_present": data.get("cheque_present", data.get("chequePresent", False)),
        "dishonour_memo": data.get("dishonour_memo", data.get("dishonourMemo", False)),
        "notice_sent": data.get("notice_sent", data.get("noticeSent", False)),
        "debt_proven": data.get("debt_proven", data.get("debtProven", False)),
        
        # Evidence quality fields
        "cheque_proof_type": data.get("cheque_proof_type", data.get("chequeProofType", data.get("original_cheque", "original"))),
        "memo_type": data.get("memo_type", data.get("memoType", data.get("dishonour_memo_type", "original"))),
        "notice_served_proof": data.get("notice_served_proof", data.get("noticeServedProof", True)),
        "debt_proof_type": data.get("debt_proof_type", data.get("debtProofType", data.get("agreement_type", "written_agreement"))),
        "within_30_days": data.get("within_30_days", data.get("within30Days", "Yes")),
        
        # Case description
        "description": data.get("description", data.get("caseDescription", data.get("case_description", ""))),
        
        # Financial details
        "amount": data.get("amount", data.get("caseAmount", data.get("debt_amount", data.get("cheque_amount", 0)))),
        
        # Party details
        "complainant_name": data.get("complainant_name", data.get("complainantName", "")),
        "accused_name": data.get("accused_name", data.get("accusedName", "")),
        "complainant_address": data.get("complainant_address", data.get("complainantAddress", "")),
        "accused_address": data.get("accused_address", data.get("accusedAddress", "")),
        
        # Cheque details
        "cheque_number": data.get("cheque_number", data.get("chequeNumber", "")),
        "cheque_date": data.get("cheque_date", data.get("chequeDate", "")),
        "bank_name": data.get("bank_name", data.get("bankName", "")),
        "cheque_amount": data.get("cheque_amount", data.get("chequeAmount", data.get("amount", 0))),
        
        # Dishonour details
        "dishonour_date": data.get("dishonour_date", data.get("dishonourDate", "")),
        "dishonour_reason": data.get("dishonour_reason", data.get("dishonourReason", "")),
        "presentation_date": data.get("presentation_date", data.get("presentationDate", "")),
        
        # Notice details
        "notice_date": data.get("notice_date", data.get("noticeDate", "")),
        "notice_mode": data.get("notice_mode", data.get("noticeMode", "")),
        "notice_received": data.get("notice_received", data.get("noticeReceived", "")),
        
        # Timeline fields
        "transaction_date": data.get("transaction_date", data.get("transactionDate", "")),
        "filing_date": data.get("filing_date", data.get("filingDate", "")),
        
        # Defence-related
        "signature_dispute": data.get("signature_dispute", data.get("signatureDispute", "")),
        "debt_denial": data.get("debt_denial", data.get("debtDenial", "")),
        "cheque_security_claim": data.get("cheque_security_claim", data.get("chequeSecurityClaim", "")),
    }
