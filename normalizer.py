import logging

logger = logging.getLogger(__name__)

def normalize_input(data):
    """
    Enhanced normalizer - extracts ALL possible fields from various input formats
    Handles both camelCase and snake_case field names, and nested wizard objects
    """
    # Extract nested objects from wizard payload
    tx_obj = data.get("transaction", {})
    cq_obj = data.get("cheque", {})
    ds_obj = data.get("dishonour", {})
    nt_obj = data.get("notice", {})
    id_obj = data.get("case_identity", {})
    pt_obj = data.get("parties", {})
    comp_obj = pt_obj.get("complainant", {})
    accu_obj = pt_obj.get("accused", {})
    meta_obj = data.get("metadata", {})

    amount = data.get("amount", data.get("caseAmount", tx_obj.get("debt_amount", cq_obj.get("cheque_amount", 0))))

    return {
        # Core identifiers
        "case_id": data.get("case_id", data.get("caseId", id_obj.get("case_id", "API_CASE"))),
        "user_id": data.get("user_id", data.get("userId", meta_obj.get("user_id", "ANONYMOUS"))),
        
        # Four pillars (boolean flags)
        "cheque_present": data.get("cheque_present", data.get("chequePresent", bool(cq_obj.get("cheque_number")))),
        "dishonour_memo": data.get("dishonour_memo", data.get("dishonourMemo", ds_obj.get("bank_memo_received", False))),
        "notice_sent": data.get("notice_sent", data.get("noticeSent", nt_obj.get("notice_sent", False))),
        "debt_proven": data.get("debt_proven", data.get("debtProven", tx_obj.get("debt_acknowledged", False))),
        
        # Evidence quality fields
        "cheque_proof_type": data.get("cheque_proof_type", cq_obj.get("cheque_proof_type", "original")),
        "memo_type": data.get("memo_type", ds_obj.get("memo_type", "original")),
        "notice_served_proof": data.get("notice_served_proof", nt_obj.get("notice_received", True)),
        "debt_proof_type": data.get("debt_proof_type", tx_obj.get("agreement_type", "written_agreement")),
        "within_30_days": data.get("within_30_days", "Yes"),
        
        # Case description
        "description": data.get("description", data.get("caseDescription", data.get("case_description", ""))),
        
        # Financial details
        "amount": amount,
        
        # Party details
        "complainant_name": data.get("complainant_name", comp_obj.get("name", "")),
        "complainant_address": data.get("complainant_address", comp_obj.get("address", "")),
        "complainant_phone": data.get("complainant_phone", comp_obj.get("phone", "")),
        "accused_name": data.get("accused_name", accu_obj.get("name", "")),
        "accused_address": data.get("accused_address", accu_obj.get("address", "")),
        
        # Cheque details
        "cheque_number": data.get("cheque_number", cq_obj.get("cheque_number", "")),
        "cheque_date": data.get("cheque_date", cq_obj.get("cheque_date", "")),
        "bank_name": data.get("bank_name", cq_obj.get("bank_name", "")),
        "cheque_amount": data.get("cheque_amount", cq_obj.get("cheque_amount", amount)),
        
        # Dishonour details
        "dishonour_date": data.get("dishonour_date", ds_obj.get("dishonour_date", "")),
        "dishonour_reason": data.get("dishonour_reason", ds_obj.get("dishonour_reason", "")),
        "presentation_date": data.get("presentation_date", ds_obj.get("presentation_date", "")),
        
        # Notice details
        "notice_date": data.get("notice_date", nt_obj.get("notice_date", "")),
        "notice_mode": data.get("notice_mode", nt_obj.get("notice_mode", "")),
        "notice_received": data.get("notice_received", nt_obj.get("notice_received", "")),
        
        # Timeline fields
        "transaction_date": data.get("transaction_date", tx_obj.get("transaction_date", "")),
        "filing_date": data.get("filing_date", id_obj.get("filing_date", "")),
        
        # New Strict Legal Fields (Expert Audit Fix)
        "complainant_type": data.get("complainant_type", id_obj.get("complainant_type", "Individual")),
        "is_authorized": data.get("is_authorized", comp_obj.get("is_authorized", False)),
        "accused_type": data.get("accused_type", accu_obj.get("type", "Individual")),
        "directors_named": data.get("directors_named", accu_obj.get("directors_named", False)),
        
        # Defence-related
        "signature_dispute": data.get("signature_dispute", data.get("signatureDispute", False)),
        "debt_denial": data.get("debt_denial", data.get("debtDenial", False)),
        "cheque_security_claim": data.get("cheque_security_claim", data.get("chequeSecurityClaim", False)),
    }
