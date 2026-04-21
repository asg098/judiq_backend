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

        NEGATIVE_RISK_ORDER = [
            "limitation_issue", "notice_defect", "notice_not_sent",
            "security_cheque", "signature_dispute", "no_debt_proof",
            "no_agreement", "cheque_misuse", "payment_already_made",
            "cheque_validity_issue", "dishonour_disputed"
        ]
        ranked_weaknesses = []
        seen_weak = set()
        for priority_concept in NEGATIVE_RISK_ORDER:
            for c in concepts:
                if c.get("concept") == priority_concept and c.get("confidence", 0) >= WEAKNESS_THRESHOLD and priority_concept not in seen_weak:
                    conf = c.get("confidence", 0)
                    severity = "CRITICAL" if conf >= 0.65 else ("HIGH" if conf >= 0.45 else "MEDIUM")
                    ranked_weaknesses.append({
                        "risk": priority_concept.replace("_", " ").title(),
                        "severity": severity,
                        "confidence": conf,
                        "detail": c.get("legal_impact", "")
                    })
                    seen_weak.add(priority_concept)
        for w in weaknesses:
            pass

        top_3_risks = ranked_weaknesses[:3]

        has_fatal = any(r["severity"] == "CRITICAL" for r in top_3_risks)
        has_high_risk = any(r["severity"] == "HIGH" for r in top_3_risks)

        if not case_data.get("notice_sent"):
            recommended_action = "SEND_NOTICE"
            decision_label = "Send Legal Notice First"
            decision_detail = "Statutory demand notice (S.138b) has not been sent. This is a mandatory pre-condition. The case cannot proceed to court without it."
            next_steps = [
                "Draft and dispatch demand notice via Registered Post (AD)",
                "Include cheque details, dishonour memo reference, and amount in notice",
                "Wait 15 days after notice delivery before filing complaint"
            ]
        elif score > 75 and not has_fatal:
            recommended_action = "FILE_COMPLAINT"
            decision_label = "File Criminal Complaint"
            decision_detail = f"Strong case ({score}/100). All legal prerequisites satisfied. Proceed to file complaint under Section 138 NI Act before the jurisdictional Magistrate."
            next_steps = [
                "Verify all original documents are in hand (cheque, memo, notice, AD card)",
                "File complaint within limitation period (1 month from cause of action)",
                "Engage an advocate to appear before the Magistrate"
            ]
        elif score >= 50 and not has_fatal:
            recommended_action = "FIX_THEN_FILE"
            decision_label = "Address Defects Before Filing"
            decision_detail = f"Moderate case ({score}/100). Foundational elements present but identifiable risks will be exploited by opposition. Strengthen evidence before filing."
            next_steps = [
                f"Priority fix: Resolve — {top_3_risks[0]['risk'] if top_3_risks else 'identified defects'}",
                "Obtain corroborating documents (bank statements, loan agreement, correspondence)",
                "Consult advocate for pre-filing assessment"
            ]
        elif score >= 40 and (has_fatal or has_high_risk):
            recommended_action = "CONSIDER_SETTLEMENT"
            decision_label = "Consider Settlement / Compounding"
            decision_detail = f"Borderline case ({score}/100) with significant defects. Litigation risk is high. A negotiated settlement under Section 147 NI Act may be the optimal resolution."
            next_steps = [
                "Issue without-prejudice settlement proposal to accused",
                "Evaluate commercial settlement vs litigation risk",
                "If settlement fails, address all defects before proceeding to court"
            ]
        else:
            recommended_action = "HIGH_RISK_DEFEND"
            decision_label = "High Risk — Prepare Defence / Do Not File"
            decision_detail = f"Weak case ({score}/100). Critical legal defects present. Filing in current state risks dismissal or acquittal. Evaluate civil recovery as an alternative."
            next_steps = [
                f"Critical defect: {top_3_risks[0]['risk'] if top_3_risks else 'Multiple defects'} must be resolved",
                "Evaluate civil suit for recovery as an alternative to criminal proceedings",
                "If already filed, prepare defence strategy immediately"
            ]

        decision = {
            "recommended_action": recommended_action,
            "decision_label": decision_label,
            "detail": decision_detail,
            "next_steps": next_steps,
            "top_3_risks": top_3_risks,
            "draft_type_generated": engine_result.get("draft_type", "LEGAL_OPINION")
        }

        return {
            "score": score,
            "verdict": verdict,
            "risk_level": risk_level,
            "analysis_confidence": confidence_score,
            "decision": decision,
            "strengths": strengths,
            "weaknesses": [f"{r['risk']} [{r['severity']} — conf: {r['confidence']:.0%}]" for r in ranked_weaknesses],
            "semantic_analysis": {
                "concepts_detected": concepts_for_response,
                "total_confidence": confidence_score,
                "count": len(concepts)
            },
            "executive_summary": {
                "score": score,
                "recommended_action": recommended_action,
                "decision_label": decision_label,
                "top_3_risks": [r["risk"] for r in top_3_risks] or ["None detected"],
                "top_strengths": strengths[:3] or ["None"],
                "next_steps": next_steps
            },
            "legal_analysis": {
                "issues": [f"{r['risk']} [{r['severity']}]" for r in ranked_weaknesses],
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
