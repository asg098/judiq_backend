import logging

logger = logging.getLogger(__name__)

def normalize_input(data):
    return {
        "case_id": data.get("case_id", data.get("caseId", "API_CASE")),
        "cheque_present": data.get("cheque_present", data.get("chequePresent", False)),
        "dishonour_memo": data.get("dishonour_memo", data.get("dishonourMemo", False)),
        "notice_sent": data.get("notice_sent", data.get("noticeSent", False)),
        "debt_proven": data.get("debt_proven", data.get("debtProven", False)),
        "description": data.get("description", data.get("caseDescription", "")),
        "amount": data.get("amount", data.get("caseAmount", 0)),
        "user_id": data.get("user_id", data.get("userId", "ANONYMOUS")),
        # OCR & Timeline Specific Fields
        "cheque_date": data.get("cheque_date", data.get("chequeDate")),
        "dishonour_date": data.get("dishonour_date", data.get("dishonourDate")),
        "notice_dispatch_date": data.get("notice_dispatch_date", data.get("noticeDispatchDate")),
        "notice_receipt_date": data.get("notice_receipt_date", data.get("noticeReceiptDate")),
        "complaint_filing_date": data.get("complaint_filing_date", data.get("complaintFilingDate")),
        "cheque_return_reason_code": data.get("cheque_return_reason_code", data.get("returnReasonCode")),
        # Vicarious Liability / Section 141 Fields
        "accused_company_name": data.get("accused_company_name", data.get("accusedCompanyName")),
        "accused_director_name": data.get("accused_director_name", data.get("accusedDirectorName")),
        "complainant_company_name": data.get("complainant_company_name", data.get("complainantCompanyName"))
    }
