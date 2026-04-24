import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def parse_date(date_str):
    """Parse date string in various formats"""
    if not date_str:
        return None
    
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %B %Y", "%B %d, %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str), fmt)
        except:
            continue
    return None

def days_between(date1_str, date2_str):
    """Calculate days between two dates"""
    d1 = parse_date(date1_str)
    d2 = parse_date(date2_str)
    if d1 and d2:
        return abs((d2 - d1).days)
    return None

class TimelineEngine:
    @staticmethod
    def generate_timeline(case_data: Dict[str, Any]) -> List[str]:
        """Generate chronological timeline with actual dates"""
        timeline = []
        
        transaction_date = case_data.get("transaction_date")
        cheque_date = case_data.get("cheque_date")
        presentation_date = case_data.get("presentation_date")
        dishonour_date = case_data.get("dishonour_date")
        notice_date = case_data.get("notice_date")
        filing_date = case_data.get("filing_date")
        
        if transaction_date:
            timeline.append(f"📋 Transaction/Debt created on {transaction_date}")
        
        if cheque_date:
            timeline.append(f"📝 Cheque issued/dated {cheque_date}")
            
            # Check if post-dated
            if transaction_date:
                days_diff = days_between(transaction_date, cheque_date)
                if days_diff and days_diff > 0:
                    timeline.append(f"   ⚠️  Post-dated by {days_diff} days")
        
        if presentation_date:
            timeline.append(f"🏦 Cheque presented to bank on {presentation_date}")
            
            # Check 3-month validity
            if cheque_date:
                days_diff = days_between(cheque_date, presentation_date)
                if days_diff:
                    if days_diff > 90:
                        timeline.append(f"   ⚠️  CRITICAL: Presented {days_diff} days after date (>3 months - may be stale)")
                    else:
                        timeline.append(f"   ✓ Presented within validity ({days_diff} days)")
        
        if dishonour_date:
            timeline.append(f"❌ Cheque dishonoured by bank on {dishonour_date}")
        
        if notice_date and dishonour_date:
            days_diff = days_between(dishonour_date, notice_date)
            if days_diff is not None:
                if days_diff <= 30:
                    timeline.append(f"📧 Legal notice sent on {notice_date} ({days_diff} days after dishonour ✓)")
                else:
                    timeline.append(f"📧 Legal notice sent on {notice_date} ({days_diff} days after dishonour ⚠️  EXCEEDS 30 DAY LIMIT)")
        elif notice_date:
            timeline.append(f"📧 Legal notice sent on {notice_date}")
        elif dishonour_date:
            timeline.append(f"   ⚠️  CRITICAL: No legal notice sent yet (mandatory within 30 days of {dishonour_date})")
        
        # Calculate cause of action
        if notice_date:
            notice_dt = parse_date(notice_date)
            if notice_dt:
                cause_of_action = notice_dt + timedelta(days=15)
                timeline.append(f"⏳ 15-day payment period expires on {cause_of_action.strftime('%Y-%m-%d')}")
                
                limitation_date = cause_of_action + timedelta(days=30)
                timeline.append(f"⚖️  Limitation period expires on {limitation_date.strftime('%Y-%m-%d')} (1 month from cause of action)")
                
                # Check if filed
                if filing_date:
                    filing_dt = parse_date(filing_date)
                    if filing_dt:
                        if filing_dt <= limitation_date:
                            timeline.append(f"✓ Complaint filed on {filing_date} (WITHIN limitation)")
                        else:
                            days_delay = (filing_dt - limitation_date).days
                            timeline.append(f"⚠️  Complaint filed on {filing_date} (DELAYED by {days_delay} days - needs condonation)")
        
        return timeline if timeline else ["Timeline data unavailable - provide dates for detailed analysis"]

    @staticmethod
    def check_limitation(case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if case is within limitation period"""
        dishonour_date = case_data.get("dishonour_date")
        notice_date = case_data.get("notice_date")
        filing_date = case_data.get("filing_date")
        
        if not all([dishonour_date, notice_date]):
            return {
                "is_barred": False,
                "days_remaining": None,
                "status": "INCOMPLETE_DATA",
                "message": "Insufficient date information to calculate limitation"
            }
        
        # Calculate notice timing
        notice_gap = days_between(dishonour_date, notice_date)
        if notice_gap and notice_gap > 30:
            return {
                "is_barred": True,
                "days_remaining": 0,
                "status": "NOTICE_LATE",
                "message": f"Notice sent {notice_gap} days after dishonour (exceeds 30-day limit)"
            }
        
        # Calculate limitation
        notice_dt = parse_date(notice_date)
        if notice_dt:
            cause_of_action = notice_dt + timedelta(days=15)
            limitation_date = cause_of_action + timedelta(days=30)
            today = datetime.now()
            
            if filing_date:
                filing_dt = parse_date(filing_date)
                if filing_dt and filing_dt > limitation_date:
                    delay_days = (filing_dt - limitation_date).days
                    return {
                        "is_barred": True,
                        "days_remaining": 0,
                        "delay_days": delay_days,
                        "status": "TIME_BARRED",
                        "message": f"Filed {delay_days} days after limitation period"
                    }
            
            if today > limitation_date:
                days_over = (today - limitation_date).days
                return {
                    "is_barred": True,
                    "days_remaining": 0,
                    "days_overdue": days_over,
                    "status": "EXPIRED",
                    "message": f"Limitation expired {days_over} days ago"
                }
            else:
                days_left = (limitation_date - today).days
                return {
                    "is_barred": False,
                    "days_remaining": days_left,
                    "limitation_date": limitation_date.strftime("%Y-%m-%d"),
                    "status": "WITHIN_TIME",
                    "message": f"{days_left} days remaining to file complaint"
                }
        
        return {
            "is_barred": False,
            "days_remaining": 30,
            "status": "ASSUMED_VALID",
            "message": "Assumed within limitation (verify dates)"
        }
