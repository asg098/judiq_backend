from semantic_engine import SemanticEngineV12
from scoring_engine import ScoringEngineV12
from defence_engine import DefenceEngineV12
from timeline_engine import TimelineEngine
from draft_engine import DraftEngine
from response_builder import ResponseBuilder
from normalizer import normalize_input
import logging

logger = logging.getLogger(__name__)

SYNTHETIC_TEXT_MAP = {
    "cheque_present":   "cheque dishonoured and bounced by bank",
    "dishonour_memo":   "bank issued dishonour memo and return slip",
    "notice_sent":      "legal notice served on accused",
    "debt_proven":      "loan agreement executed and legally enforceable debt established",
}

STRUCTURAL_NEGATIVE_CONCEPTS = {
    "debt_proven": {
        "concept": "no_debt_proof",
        "confidence": 0.72,
        "matched_phrases": ["debt not proven — structured signal"],
        "legal_impact": "challenges legal enforceability under S.139"
    },
    "notice_sent": {
        "concept": "notice_defect",
        "confidence": 0.85,
        "matched_phrases": ["notice not sent — structural signal"],
        "legal_impact": "mandatory statutory requirement under S.138(b)"
    },
}

STRUCTURED_KEYS = {
    "cheque_present", "chequePresent", "dishonour_memo", "dishonourMemo",
    "notice_sent", "noticeSent", "debt_proven", "debtProven"
}


def _has_any_input(raw_data: dict, case_data: dict) -> bool:
    """Return True if there is any meaningful input to analyse."""
    has_description = bool(case_data.get("description", "").strip())
    has_flags = any(raw_data.get(k) for k in STRUCTURED_KEYS)
    return has_description or has_flags


class JudiQEngine:
    @classmethod
    def analyze_case(cls, raw_data: dict):
        case_data = normalize_input(raw_data)

        # ── Guard: nothing to analyse ─────────────────────────────────────────
        if not _has_any_input(raw_data, case_data):
            return {
                "score": 0,
                "verdict": "INSUFFICIENT DATA",
                "risk_level": "UNKNOWN",
                "analysis_confidence": None,
                "decision": {
                    "recommended_action": "PROVIDE_INPUT",
                    "decision_label": "Provide Case Details",
                    "detail": "No case description or checklist data was submitted. Please describe the facts or use the checklist to enable analysis.",
                    "next_steps": [
                        "Enter a description of the case facts, OR",
                        "Fill in the checklist (cheque present, notice sent, etc.)",
                        "Then resubmit for a full analysis"
                    ],
                    "top_3_risks": [],
                    "draft_type_generated": "LEGAL_OPINION"
                },
                "strengths": [],
                "weaknesses": [],
                "semantic_analysis": {"concepts_detected": [], "total_confidence": 0, "count": 0},
                "executive_summary": {
                    "score": 0,
                    "recommended_action": "PROVIDE_INPUT",
                    "decision_label": "Provide Case Details",
                    "top_3_risks": [],
                    "top_strengths": [],
                    "next_steps": []
                },
                "legal_analysis": {"issues": [], "strengths": [], "reasoning": [], "breakdown": []},
                "defence_strategy": [],
                "draft": "",
                "draft_type": "LEGAL_OPINION",
                "timeline": [],
            }

        # ── Build analysis text ───────────────────────────────────────────────
        text = case_data.get("description", "").strip()
        if not text:
            parts = [phrase for key, phrase in SYNTHETIC_TEXT_MAP.items() if case_data.get(key)]
            text = ". ".join(parts)

        print(f"DEBUG TEXT: {text}")

        semantic_result = SemanticEngineV12.analyze_text(text)
        concepts = semantic_result.get("concepts_detected", [])
        existing_concepts = {c["concept"] for c in concepts}

        # Inject structural negative signals for missing pillars (structured mode only)
        if any(raw_data.get(k) is not None for k in STRUCTURED_KEYS):
            for pillar_key, signal in STRUCTURAL_NEGATIVE_CONCEPTS.items():
                if not case_data.get(pillar_key) and signal["concept"] not in existing_concepts:
                    concepts.append(dict(signal))
                    existing_concepts.add(signal["concept"])

        # Inject positive fallback only if semantic returned nothing at all
        if not concepts:
            if case_data.get("cheque_present"):
                concepts.append({"concept": "cheque_bounce", "confidence": 0.80, "matched_phrases": ["fallback: cheque present"], "legal_impact": "establishes core Section 138 NI Act offence"})
            if case_data.get("notice_sent"):
                concepts.append({"concept": "legal_notice_compliance", "confidence": 0.72, "matched_phrases": ["fallback: notice sent"], "legal_impact": "satisfies mandatory notice requirement under S.138(b)"})
            if case_data.get("debt_proven"):
                concepts.append({"concept": "legally_enforceable_debt", "confidence": 0.75, "matched_phrases": ["fallback: debt proven"], "legal_impact": "establishes legally enforceable liability under S.139"})

        print(f"DEBUG CONCEPTS: {[c['concept'] for c in concepts]}")

        timeline = TimelineEngine.generate_timeline(case_data)
        TimelineEngine.check_limitation(case_data)

        evidence = {
            "strength": "STRONG" if (case_data.get("cheque_present") and case_data.get("dishonour_memo")) else "WEAK",
            "score_multiplier": 1.0 if case_data.get("cheque_present") else 0.8
        }

        # Pass raw_data so the scoring engine can detect structured vs description-only
        scoring_result = ScoringEngineV12.calculate_score_with_trace(
            case_data, concepts, [], evidence, raw_input=raw_data
        )

        defences = DefenceEngineV12.generate_ranked_defences(
            concepts, case_data, scoring_result['final_score']
        )

        final_score = scoring_result["final_score"]

        from draft_engine import decide_draft_type
        draft_type = decide_draft_type(final_score, concepts, case_data)
        draft = DraftEngine.generate_draft(draft_type, final_score, concepts, case_data)

        engine_output = {
            **scoring_result,
            "concepts": concepts,
            "defences": defences,
            "timeline": timeline,
            "draft": draft,
            "draft_type": draft_type
        }

        return ResponseBuilder.build_final_response(engine_output, case_data)
