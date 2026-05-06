import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class TimelineEngine:
    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def generate_timeline(case_data: Dict[str, Any]) -> List[str]:
        timeline = []
        cheque_date = case_data.get("cheque_date")
        dishonour_date = case_data.get("dishonour_date")
        notice_dispatch = case_data.get("notice_dispatch_date")
        notice_receipt = case_data.get("notice_receipt_date")
        complaint_date = case_data.get("complaint_filing_date")

        if cheque_date:
            timeline.append(f"Cheque issued on {cheque_date}")
        if dishonour_date:
            timeline.append(f"Cheque dishonoured by bank on {dishonour_date}")
        if notice_dispatch:
            timeline.append(f"Demand notice dispatched on {notice_dispatch}")
        if notice_receipt:
            timeline.append(f"Demand notice served on {notice_receipt}")
        if complaint_date:
            timeline.append(f"Complaint filed on {complaint_date}")

        return timeline or ["Timeline data unavailable"]

    @classmethod
    def check_limitation(cls, case_data: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "is_barred": False,
            "fatal_errors": [],
            "warnings": []
        }
        
        cheque_date = cls._parse_date(case_data.get("cheque_date"))
        dishonour_date = cls._parse_date(case_data.get("dishonour_date"))
        notice_dispatch = cls._parse_date(case_data.get("notice_dispatch_date"))
        notice_receipt = cls._parse_date(case_data.get("notice_receipt_date"))
        complaint_date = cls._parse_date(case_data.get("complaint_filing_date"))
        
        now = datetime.now()

        # Check for impossible future dates
        for d_name, d_val in [("Cheque date", cheque_date), ("Dishonour date", dishonour_date), 
                              ("Notice dispatch", notice_dispatch), ("Notice receipt", notice_receipt), 
                              ("Complaint date", complaint_date)]:
            if d_val and d_val > now:
                result["is_barred"] = True
                result["fatal_errors"].append(f"Impossible Date: {d_name} is in the future.")

        # Rule 0: Cheque validity (3 months in India)
        if cheque_date and dishonour_date:
            validity_days = (dishonour_date - cheque_date).days
            if validity_days > 90:
                result["is_barred"] = True
                result["fatal_errors"].append(f"Cheque presented {validity_days} days after issue (stale cheque limit: 90 days).")
            elif validity_days < 0:
                result["fatal_errors"].append("Cheque dishonoured BEFORE it was issued.")

        # Rule 1: Notice within 30 days of dishonour
        if dishonour_date and notice_dispatch:
            days = (notice_dispatch - dishonour_date).days
            if days > 30:
                result["is_barred"] = True
                result["fatal_errors"].append(f"Notice dispatched {days} days after dishonour (limit: 30 days).")
            elif days < 0:
                result["fatal_errors"].append("Notice dispatched BEFORE cheque dishonour.")
        elif dishonour_date and not notice_dispatch:
            result["warnings"].append("Dishonour date present but notice dispatch date is missing.")

        # Rule 2: 15-day waiting period after receipt
        if notice_receipt and complaint_date:
            days_waited = (complaint_date - notice_receipt).days
            if days_waited < 15:
                result["is_barred"] = True
                result["fatal_errors"].append(f"Complaint filed prematurely. Waited {days_waited} days (minimum: 15 days).")

        # Rule 3: Complaint within 30 days after the 15-day period (45 days from receipt)
        if notice_receipt and complaint_date:
            days_from_receipt = (complaint_date - notice_receipt).days
            if days_from_receipt > 45:
                result["is_barred"] = True
                result["fatal_errors"].append(f"Complaint filed {days_from_receipt - 15} days after cause of action (limit: 30 days).")

        return result
