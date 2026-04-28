import sys
sys.path.append('c:/Users/Atharva/OneDrive/Desktop/Level_0judiq')
from engine_core import JudiQEngine

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

result = JudiQEngine.analyze_case(perfect_case)
print(result['issues'])
