import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class TimelineEngine:
    @staticmethod
    def generate_timeline(case_data: Dict[str, Any]) -> List[str]:
        timeline = []
        cheque_date = case_data.get("cheque_date")
        dishonour_date = case_data.get("dishonour_date")
        notice_date = case_data.get("notice_date")
        if cheque_date:
            timeline.append(f"Cheque issued on {cheque_date}")
        if dishonour_date:
            timeline.append(f"Cheque dishonoured by bank on {dishonour_date}")
        if notice_date:
            timeline.append(f"Demand notice served on {notice_date}")
        if dishonour_date and not notice_date:
            timeline.append("CRITICAL: Statutory notice period currently pending or missed.")
        return timeline or ["Timeline data unavailable"]

    @staticmethod
    def check_limitation(case_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"is_barred": False, "days_remaining": 30}
