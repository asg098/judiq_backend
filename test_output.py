import json
from engine_core import JudiQEngine

def get_cases():
    return [
        {
            "case_id": "CASE_PERFECT_TIMELINE",
            "caseDescription": "Perfect timeline case.",
            "chequePresent": True, "dishonourMemo": True, "noticeSent": True, "debtProven": True,
            "chequeDate": "2023-01-01",
            "dishonourDate": "2023-01-15",
            "noticeDispatchDate": "2023-01-20",
            "noticeReceiptDate": "2023-01-25",
            "complaintFilingDate": "2023-03-01" # 15 days after 01-25 is 02-09. Filed within 30 days of that.
        },
        {
            "case_id": "CASE_STALE_CHEQUE",
            "caseDescription": "Cheque presented after 3 months.",
            "chequePresent": True, "dishonourMemo": True, "noticeSent": True, "debtProven": True,
            "chequeDate": "2022-01-01",
            "dishonourDate": "2022-05-01", # 120 days later
            "noticeDispatchDate": "2022-05-15"
        },
        {
            "case_id": "CASE_FUTURE_DATE_ERROR",
            "caseDescription": "A date from 2050.",
            "chequePresent": True, "dishonourMemo": True,
            "chequeDate": "2050-01-01",
            "dishonourDate": "2050-01-10"
        },
        {
            "case_id": "CASE_LATE_NOTICE",
            "caseDescription": "Notice sent late.",
            "chequePresent": True, "dishonourMemo": True, "noticeSent": True, "debtProven": True,
            "dishonourDate": "2023-01-01",
            "noticeDispatchDate": "2023-02-15", # 45 days later
        },
        {
            "case_id": "CASE_PREMATURE_COMPLAINT",
            "caseDescription": "Filed before 15 days.",
            "chequePresent": True, "dishonourMemo": True, "noticeSent": True, "debtProven": True,
            "dishonourDate": "2023-01-01",
            "noticeDispatchDate": "2023-01-15",
            "noticeReceiptDate": "2023-01-20",
            "complaintFilingDate": "2023-01-25" # Only 5 days wait
        },
        {
            "case_id": "CASE_LATE_COMPLAINT",
            "caseDescription": "Filed too late.",
            "chequePresent": True, "dishonourMemo": True, "noticeSent": True, "debtProven": True,
            "dishonourDate": "2023-01-01",
            "noticeDispatchDate": "2023-01-10",
            "noticeReceiptDate": "2023-01-15",
            "complaintFilingDate": "2023-04-15" # 3 months later
        },
        {
            "case_id": "CASE_MISSING_NOTICE_DISPATCH",
            "caseDescription": "We have dishonour date but no dispatch date.",
            "chequePresent": True, "dishonourMemo": True,
            "dishonourDate": "2023-01-01"
        }
    ]

def run_audit_suite():
    cases = get_cases()
    results = []
    print("--- JudiQ Zero-Mistake Procedural Audit Suite ---")
    for c in cases:
        res = JudiQEngine.analyze_case(c)
        limitation = res.get("data", {}).get("limitation_check", {})
        verdict = res.get("verdict", "UNKNOWN")
        score = res.get("score", 0)
        
        errors = limitation.get("fatal_errors", [])
        
        print(f"CASE: {c['case_id']}")
        print(f"  Verdict: {verdict} (Score: {score})")
        if errors:
            print("  FATAL ERRORS:")
            for err in errors:
                print(f"    - {err}")
        print("-" * 50)

if __name__ == "__main__":
    run_audit_suite()
