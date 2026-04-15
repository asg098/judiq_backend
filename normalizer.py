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
        "user_id": data.get("user_id", data.get("userId", "ANONYMOUS"))
    }
