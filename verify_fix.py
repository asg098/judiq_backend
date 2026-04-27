import sys
import os
from engine_core import JudiQEngine

# Minimal perfect case data
perfect_case = {
    "cheque_present": True,
    "dishonour_memo": True,
    "notice_sent": True,
    "debt_proven": True,
    "description": "Original cheque 123456 for 100000 bounced. Legal notice sent within 30 days. Loan agreement exists.",
    "cheque_proof_type": "original",
    "memo_type": "original",
    "notice_served_proof": True,
    "within_30_days": "Yes",
    "notice_mode": "registered post",
    "debt_proof_type": "loan_agreement"
}

try:
    result = JudiQEngine.analyze_case(perfect_case)
    print(f"SCORE: {result['score']}")
    print(f"ISSUES: {result['issues']}")
    print(f"WEAKNESSES: {result['weaknesses']}")
    
    if result['score'] > 91:
        print(f"SUCCESS: Score is {result['score']}, which is above the old 91 cap.")
    else:
        print(f"FAILURE: Score is still {result['score']}, which is at or below the old 91 cap.")
        
    if len(result['issues']) >= 1:
        print(f"SUCCESS: {len(result['issues'])} issues detected (including litigation risk).")
    else:
        print("FAILURE: No issues detected even though litigation risk should be present!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
