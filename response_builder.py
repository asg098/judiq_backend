import re
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def ensure_list(x):
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def ensure_dict(x):
    if x is None: return {}
    if isinstance(x, dict): return x
    return {}

def _convert_to_lawyer_language(raw_trace: list) -> list:
    _PHRASE_MAP = [
        (r"\+\d+\s+cheque\s+present", "Presence of a cheque supports the foundation of the claim under Section 138 NI Act."),
        (r"\+\d+\s+cheque", "The negotiable instrument (cheque) is on record, establishing the primary basis."),
        (r"-\d+\s+no\s+cheque", "Absence of the foundational instrument required for a Section 138 proceeding."),
        (r"\+\d+\s+dishonour\s+memo", "An official bank dishonour memo provides documentary confirmation of the return."),
        (r"\+\d+\s+notice\s+sent", "Service of the statutory demand notice satisfies Section 138(b) compliance."),
        (r"-\d+\s+no\s+notice", "The mandatory statutory demand notice has not been served (procedural bar)."),
        (r"\+\d+\s+debt\s+proven", "Legally enforceable debt or liability is documented via independent evidence."),
        (r"-\d+\s+debt\s+not\s+proven", "Absence of proof of underlying debt weakens the presumption under S.139.")
    ]
    clean_trace = []
    for item in raw_trace:
        matched = False
        for pattern, substitution in _PHRASE_MAP:
            if re.search(pattern, str(item), re.IGNORECASE):
                clean_trace.append(substitution)
                matched = True
                break
        if not matched:
            cleaned = re.sub(r"^[+-]\d+\s+", "", str(item)).strip()
            if cleaned:
                clean_trace.append(cleaned)
    return clean_trace

class ResponseBuilder:
    @staticmethod
    def build_final_response(engine_result: Dict[str, Any], case_data: Dict[str, Any]) -> Dict[str, Any]:
        score = engine_result.get("final_score", 0)
        trace = engine_result.get("reasoning_trace", [])
        breakdown = engine_result.get("score_breakdown", [])
        verdict = "STRONG CASE"
        if score < 40: verdict = "WEAK CASE / HIGH RISK"
        elif score < 70: verdict = "MODERATE CASE"
        risk_level = "LOW"
        if score < 50: risk_level = "CRITICAL"
        elif score < 75: risk_level = "MEDIUM"
        concepts = engine_result.get("concepts", [])
        risks = [c.get("concept").replace('_', ' ').title() for c in concepts if c.get("confidence", 0) > 0.4][:3]
        strengths = []
        if case_data.get("cheque_present"): strengths.append("Instrument Possession")
        if case_data.get("dishonour_memo"): strengths.append("Bank Return Memo")
        if case_data.get("notice_sent"): strengths.append("Compliance (Notice)")
        lawyer_reasoning = _convert_to_lawyer_language(trace)
        return {
            "score": score,
            "verdict": verdict,
            "risk_level": risk_level,
            "executive_summary": {
                "score": score,
                "top_risks": risks or ["None detected"],
                "top_strengths": strengths[:3] or ["None"],
                "next_action": "Proceed with filing" if score > 70 else "Address critical defects before litigation"
            },
            "legal_analysis": {
                "issues": risks,
                "strengths": strengths,
                "reasoning": lawyer_reasoning,
                "breakdown": breakdown
            },
            "defence_strategy": engine_result.get("defences", []),
            "timestamp": datetime.now().isoformat(),
            "engine_version": "v19.0-SANKATMOCHAN-v6"
        }
