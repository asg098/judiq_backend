from engine_core import JudiQEngine
import json

case_data = {
    "case_id": "TEST-READINESS-001",
    "amount": 450000,
    "description": "Loan of 4.5L given in cash for business expansion. Accused issued a cheque which bounced for Insufficient Funds. I have WhatsApp chats where he admits the debt.",
    "cheque_present": True,
    "dishonour_memo": True,
    "notice_sent": True,
    "within_30_days": "No", # The 5-day delay
    "delay_days": 5,
    "complainant_name": "Atharva",
    "accused_name": "Accused Party",
    "accused_type": "Individual",
    "analysis_mode": "detailed",
    "communication_records": True
}

try:
    result = JudiQEngine.analyze_case(case_data)
    print("--- TRIAL READINESS REPORT (v20.0) ---")
    print(f"VERDICT: {result['verdict']}")
    print(f"SCORE: {result['score']}/100")
    print(f"READINESS INDEX (CRI): {result.get('cri_score', 'N/A')}/100")
    print("\n--- IMPROVEMENT METRICS ---")
    metrics = result.get('advocate_audit', {}).get('improvement_metrics', [])
    for m in metrics:
        print(f"[{m['area']}] Current: {m['current']} -> Target: {m['targeted']}")
    
    print("\n--- TOP CROSS-EXAMINATION ATTACKS ---")
    for i, attack in enumerate(result.get('cross_exam', []), 1):
        print(f"{i}. QUESTION: {attack['question']}")
        print(f"   OBJECTIVE: {attack['objective']}")
        print(f"   PREPARATION: {attack['preparation']}\n")

    print("--- SETTLEMENT OPTIMIZER ---")
    print(result.get('litigation_strategy', {}).get('settlement_strategy', 'N/A'))
    
except Exception as e:
    print(f"Error during analysis: {e}")
    import traceback
    traceback.print_exc()
