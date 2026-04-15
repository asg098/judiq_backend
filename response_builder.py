import re
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def ensure_list(x):
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

NEGATIVE_CONCEPTS = {
    "signature_dispute", "notice_defect", "no_debt_proof", "security_cheque",
    "cheque_misuse", "limitation_issue", "payment_already_made", "dishonour_disputed",
    "cheque_validity_issue", "no_agreement"
}

POSITIVE_CONCEPTS = {
    "cheque_bounce", "legal_notice_compliance", "legally_enforceable_debt",
    "strong_documentary_evidence"
}

WEAKNESS_THRESHOLD = 0.22
STRENGTH_THRESHOLD = 0.45

def _convert_to_lawyer_language(raw_trace: list) -> list:
    _PHRASE_MAP = [
        (r"\+\d+\s+instrument\s+present", "Presence of a cheque supports the foundation of the claim under Section 138 NI Act."),
        (r"\+\d+\s+cheque", "The negotiable instrument (cheque) is on record, establishing the primary basis."),
        (r"-\d+\s+instrument\s+missing", "Absence of the foundational instrument required for a Section 138 proceeding."),
        (r"\+\d+\s+memo\s+available", "An official bank dishonour memo provides documentary confirmation of the return."),
        (r"\+\d+\s+notice\s+compliance", "Service of the statutory demand notice satisfies Section 138(b) compliance."),
        (r"-\d+\s+notice\s+defect", "The mandatory statutory demand notice has not been served — a procedural bar."),
        (r"\+\d+\s+debt\s+provenance", "Legally enforceable debt or liability is documented via independent evidence."),
        (r"-\d+\s+debt\s+not\s+established", "Absence of proof of underlying debt weakens the evidentiary presumption under S.139."),
        (r"\+\d+\s+strong\s+case\s+synergy", "All four legal pillars are satisfied: instrument, dishonour, notice, and debt."),
        (r"-\d+\s+notice\s+defect\s+\(fatal\)", "Failure to serve statutory demand notice within 30 days is a fatal procedural defect."),
        (r"-\d+\s+debt\s+not\s+established", "No legally enforceable debt proven — S.139 presumption significantly weakened."),
    ]
    clean_trace = []
    seen = set()
    for item in raw_trace:
        matched = False
        for pattern, substitution in _PHRASE_MAP:
            if re.search(pattern, str(item), re.IGNORECASE):
                if substitution not in seen:
                    clean_trace.append(substitution)
                    seen.add(substitution)
                matched = True
                break
        if not matched:
            cleaned = re.sub(r"^[+-]\d+\s+", "", str(item)).strip()
            if cleaned and not cleaned.startswith("Base score") and not cleaned.startswith("Final score") and not cleaned.startswith("Applied") and cleaned not in seen:
                clean_trace.append(cleaned)
                seen.add(cleaned)
    return clean_trace


class ResponseBuilder:
    @staticmethod
    def build_final_response(engine_result: Dict[str, Any], case_data: Dict[str, Any]) -> Dict[str, Any]:
        score = engine_result.get("final_score", 0)
        trace = engine_result.get("reasoning_trace", [])
        breakdown = engine_result.get("score_breakdown", [])
        concepts = engine_result.get("concepts", [])

        verdict = "STRONG CASE"
        if score < 40: verdict = "WEAK CASE / HIGH RISK"
        elif score < 70: verdict = "MODERATE CASE"

        risk_level = "LOW"
        if score < 50: risk_level = "CRITICAL"
        elif score < 75: risk_level = "MEDIUM"

        strengths = []
        weaknesses = []

        if case_data.get("cheque_present"):   strengths.append("Negotiable instrument (cheque) secured")
        if case_data.get("dishonour_memo"):   strengths.append("Bank dishonour memo / return slip available")
        if case_data.get("notice_sent"):      strengths.append("Statutory demand notice served (S.138b)")
        if case_data.get("debt_proven"):      strengths.append("Legally enforceable debt established")

        for c in concepts:
            concept_name = c.get("concept", "")
            conf = c.get("confidence", 0)
            label = concept_name.replace('_', ' ').title()

            if concept_name in NEGATIVE_CONCEPTS and conf >= WEAKNESS_THRESHOLD:
                severity = "CRITICAL" if conf >= 0.65 else ("HIGH" if conf >= 0.45 else "MEDIUM")
                weaknesses.append(f"{label} [{severity} — conf: {conf:.0%}]")

            elif concept_name in POSITIVE_CONCEPTS and conf >= STRENGTH_THRESHOLD:
                strengths.append(f"{label} detected (conf: {conf:.0%})")

        confidence_score = round(sum(c.get("confidence", 0) for c in concepts) / len(concepts), 2) if concepts else None
        lawyer_reasoning = _convert_to_lawyer_language(trace)

        concepts_for_response = [
            {
                "concept": c.get("concept", ""),
                "confidence": c.get("confidence", 0),
                "legal_impact": c.get("legal_impact", ""),
                "matched_phrases": c.get("matched_phrases", [])
            }
            for c in concepts
        ]

        return {
            "score": score,
            "verdict": verdict,
            "risk_level": risk_level,
            "analysis_confidence": confidence_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "semantic_analysis": {
                "concepts_detected": concepts_for_response,
                "total_confidence": confidence_score,
                "count": len(concepts)
            },
            "executive_summary": {
                "score": score,
                "top_risks": weaknesses[:3] or ["None detected"],
                "top_strengths": strengths[:3] or ["None"],
                "next_action": "Proceed with filing" if score > 70 else "Address critical defects before litigation"
            },
            "legal_analysis": {
                "issues": weaknesses,
                "strengths": strengths,
                "reasoning": lawyer_reasoning,
                "breakdown": breakdown
            },
            "defence_strategy": engine_result.get("defences", []),
            "draft": engine_result.get("draft", ""),
            "draft_type": engine_result.get("draft_type", "LEGAL_OPINION"),
            "timeline": engine_result.get("timeline", []),
            "timestamp": datetime.now().isoformat(),
            "engine_version": "v19.0-SANKATMOCHAN-v6.5"
        }
