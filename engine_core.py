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

class JudiQEngine:
    @classmethod
    def analyze_case(cls, raw_data: dict):
        case_data = normalize_input(raw_data)

        text = case_data.get("description", "").strip()
        if not text:
            parts = [phrase for key, phrase in SYNTHETIC_TEXT_MAP.items() if case_data.get(key)]
            text = ". ".join(parts)

        print(f"DEBUG TEXT: {text}")

        semantic_result = SemanticEngineV12.analyze_text(text)
        concepts = semantic_result.get("concepts_detected", [])

        if not concepts:
            detected_names = set()
            if case_data.get("cheque_present"):
                concepts.append({"concept": "cheque_bounce", "confidence": 0.80, "matched_phrases": ["cheque bounced"], "legal_impact": "establishes core Section 138 NI Act offence"})
                detected_names.add("cheque_bounce")
            if case_data.get("notice_sent"):
                concepts.append({"concept": "legal_notice_compliance", "confidence": 0.72, "matched_phrases": ["legal notice served"], "legal_impact": "satisfies mandatory notice requirement under S.138(b)"})
                detected_names.add("legal_notice_compliance")
            if case_data.get("debt_proven"):
                concepts.append({"concept": "legally_enforceable_debt", "confidence": 0.75, "matched_phrases": ["loan agreement"], "legal_impact": "establishes legally enforceable liability under S.139"})
                detected_names.add("legally_enforceable_debt")

        print(f"DEBUG CONCEPTS: {[c['concept'] for c in concepts]}")

        timeline = TimelineEngine.generate_timeline(case_data)
        TimelineEngine.check_limitation(case_data)

        evidence = {
            "strength": "STRONG" if (case_data.get("cheque_present") and case_data.get("dishonour_memo")) else "WEAK",
            "score_multiplier": 1.0 if case_data.get("cheque_present") else 0.8
        }

        scoring_result = ScoringEngineV12.calculate_score_with_trace(
            case_data, concepts, [], evidence
        )

        defences = DefenceEngineV12.generate_ranked_defences(
            concepts, case_data, scoring_result['final_score']
        )

        final_score = scoring_result["final_score"]
        verdict = "STRONG" if final_score > 70 else ("MODERATE" if final_score > 40 else "WEAK")

        draft = DraftEngine.generate_opinion({
            "score": final_score,
            "verdict": verdict,
            "concepts": concepts,
            "case_data": case_data
        })

        engine_output = {
            **scoring_result,
            "concepts": concepts,
            "defences": defences,
            "timeline": timeline,
            "draft": draft
        }

        return ResponseBuilder.build_final_response(engine_output, case_data)
