import json
from engine_core import JudiQEngine

def get_cases():
    return [
        {
            "case_id": "CASE_ALMOST_PERFECT",
            "description": "Bounced cheque of 10L. Written agreement exists. Notice sent via AD card.",
            "cheque_present": True,
            "cheque_proof_type": "original",
            "dishonour_memo": True,
            "memo_type": "original",
            "notice_sent": True,
            "notice_served_proof": True,
            "debt_proven": True,
            "debt_proof_type": "loan_agreement",
            "amount": 1000000
        },
        {
            "case_id": "CASE_VERBAL_DEBT",
            "description": "Bounced cheque of 50k. No written agreement, only verbal promise.",
            "cheque_present": True,
            "dishonour_memo": True,
            "notice_sent": True,
            "debt_proven": True,
            "debt_proof_type": "verbal",
            "amount": 50000
        },
        {
            "case_id": "CASE_XEROX_NOTICE_ISSUE",
            "description": "Bounced cheque. Notice sent but proof of service missing. Cheque is a photocopy.",
            "cheque_present": True,
            "cheque_proof_type": "xerox",
            "dishonour_memo": True,
            "notice_sent": True,
            "notice_served_proof": False,
            "debt_proven": True,
            "debt_proof_type": "invoice"
        }
    ]

def generate_multi_json():
    cases = get_cases()
    results = []
    for c in cases:
        res = JudiQEngine.analyze_case(c)
        results.append({
            "case_id": c["case_id"],
            "score": res["score"],
            "verdict": res["verdict"],
            "top_trace": res["legal_analysis"]["reasoning"][:3]
        })
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    generate_multi_json()
