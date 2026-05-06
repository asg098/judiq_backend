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

class JudiQEngine:
    @classmethod
    def analyze_case(cls, raw_data: dict):
        case_data = normalize_input(raw_data)

        text = (case_data.get("description") or "").strip()
        if not text:
            parts = [phrase for key, phrase in SYNTHETIC_TEXT_MAP.items() if case_data.get(key)]
            text = ". ".join(parts)

        print(f"DEBUG TEXT: {text}")

        semantic_result = SemanticEngineV12.analyze_text(text)
        concepts = semantic_result.get("concepts_detected", [])

        existing_concepts = {c["concept"] for c in concepts}

        # Inject structural negative signals for missing pillars (always)
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
        limitation_check = TimelineEngine.check_limitation(case_data)

        if limitation_check.get("is_barred"):
            for err in limitation_check.get("fatal_errors", []):
                concepts.append({
                    "concept": "limitation_barred",
                    "confidence": 1.0,
                    "matched_phrases": [err],
                    "legal_impact": "FATAL: Case is barred by limitation under Section 138/142 NI Act."
                })

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
        if limitation_check.get("is_barred"):
            final_score = min(final_score, 10)  # Crush score if timeline barred
            scoring_result["final_score"] = final_score
            verdict = "FATAL (TIME-BARRED)"
        else:
            verdict = "STRONG" if final_score > 70 else ("MODERATE" if final_score > 40 else "WEAK")

        from draft_engine import decide_draft_type
        draft_type = decide_draft_type(final_score, concepts, case_data)
        draft = DraftEngine.generate_draft(draft_type, final_score, concepts, case_data)

        # Generate Section 65B Certificate if digital evidence is present
        auxiliary_drafts = {}
        if case_data.get("digital_evidence") or "whatsapp" in text.lower() or "email" in text.lower():
            auxiliary_drafts["SECTION_65B_CERTIFICATE"] = DraftEngine.generate_draft("SECTION_65B_CERTIFICATE", final_score, concepts, case_data)

        engine_output = {
            **scoring_result,
            "concepts": concepts,
            "defences": defences,
            "timeline": timeline,
            "limitation_check": limitation_check,
            "draft": draft,
            "draft_type": draft_type,
            "auxiliary_drafts": auxiliary_drafts
        }

        return ResponseBuilder.build_final_response(engine_output, case_data)
