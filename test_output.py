import json
from engine_core import JudiQEngine
def get_cases():
    return [
        {
            "case_id": "CASE_ALMOST_PERFECT",
            "caseDescription": "Bounced cheque of 10L. Written agreement exists. Notice sent via AD card.",
            "chequePresent": True,
            "cheque_proof_type": "original",
            "dishonourMemo": True,
            "memo_type": "original",
            "noticeSent": True,
            "notice_served_proof": True,
            "debtProven": True,
            "debt_proof_type": "loan_agreement",
            "amount": 1000000
        },
        {
            "case_id": "CASE_VERBAL_DEBT",
            "caseDescription": "Bounced cheque of 50k. No written agreement, only verbal promise.",
            "chequePresent": True,
            "dishonourMemo": True,
            "noticeSent": True,
            "debtProven": True,
            "debt_proof_type": "verbal",
            "amount": 50000
        },
        {
            "case_id": "CASE_XEROX_NOTICE_ISSUE",
            "caseDescription": "Bounced cheque. Notice sent but proof of service missing. Cheque is a photocopy.",
            "chequePresent": True,
            "cheque_proof_type": "xerox",
            "dishonourMemo": True,
            "noticeSent": True,
            "notice_served_proof": False,
            "debtProven": True,
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
            "score": res.get("score"),
            "verdict": res.get("verdict"),
            "issues_count": len(res.get("issues", []))
        })
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    generate_multi_json()
