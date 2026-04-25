from semantic_engine  import SemanticEngineV12
from scoring_engine   import ScoringEngineV12
from defence_engine   import DefenceEngineV12
from timeline_engine  import TimelineEngine
from draft_engine     import DraftEngine, decide_draft_type
from response_builder import ResponseBuilder
from normalizer       import normalize_input, validate_minimum_viability, ValidationError
from reasoning_engine import ReasoningEngine
from decision_support_engine import DecisionSupportEngine
import logging

logger = logging.getLogger(__name__)

# ── Synthetic text map ─────────────────────────────────────────────────────────
SYNTHETIC_TEXT_MAP = {
    "cheque_present":  "cheque dishonoured and bounced by bank",
    "dishonour_memo":  "bank issued dishonour memo and return slip",
    "notice_sent":     "legal notice served on accused",
    "debt_proven":     "loan agreement executed and legally enforceable debt established",
}

# ── Structural negative signals ────────────────────────────────────────────────
STRUCTURAL_NEGATIVE_CONCEPTS = {
    "debt_proven": {
        "concept": "no_debt_proof",
        "confidence": 0.72,
        "matched_phrases": ["debt not proven — structural signal"],
        "legal_impact": "Challenges legal enforceability under S.139."
    },
    "notice_sent": {
        "concept": "notice_defect",
        "confidence": 0.88,
        "matched_phrases": ["notice not sent — structural signal"],
        "legal_impact": "Mandatory requirement under S.138(b)."
    },
}

# ── Safe fallback builders ─────────────────────────────────────────────────────

def _safe_call(fn, *args, fallback, context=""):
    """Call fn(*args); on any exception return fallback and log the error."""
    try:
        return fn(*args)
    except Exception as exc:
        logger.error(f"[ENGINE] {context} failed: {exc}", exc_info=True)
        return fallback


class JudiQEngine:
    """
    Central orchestrator — fully fault-tolerant.
    Each pipeline step is independently guarded so a failure in one layer
    NEVER crashes the entire analysis.
    """

    @classmethod
    def analyze_case(cls, raw_data: dict) -> dict:

        # ── Hard gate ──────────────────────────────────────────────────────────
        validate_minimum_viability(raw_data)

        # ── Step 1: Normalise ──────────────────────────────────────────────────
        case_data = normalize_input(raw_data)
        logger.info(f"[JUDIQ] Analyzing case: {case_data.get('case_id', 'ANON')}")

        # ── Step 2: Semantic analysis ──────────────────────────────────────────
        text = case_data.get("description", "").strip()
        if not text:
            parts = [phrase for key, phrase in SYNTHETIC_TEXT_MAP.items() if case_data.get(key)]
            text = ". ".join(parts)

        semantic_result = _safe_call(
            SemanticEngineV12.analyze_text, text,
            fallback={"concepts_detected": []},
            context="SemanticEngine"
        )
        concepts: list = semantic_result.get("concepts_detected") or []
        existing_concepts = {c["concept"] for c in concepts if isinstance(c, dict) and "concept" in c}

        # ── Step 3: Inject structural negative signals ─────────────────────────
        for pillar_key, signal in STRUCTURAL_NEGATIVE_CONCEPTS.items():
            if not case_data.get(pillar_key) and signal["concept"] not in existing_concepts:
                concepts.append(dict(signal))
                existing_concepts.add(signal["concept"])

        # Positive fallback — only if nothing at all was detected
        if not any(c.get("concept") not in {"no_debt_proof", "notice_defect"} for c in concepts):
            if case_data.get("cheque_present"):
                concepts.append({"concept": "cheque_bounce", "confidence": 0.80,
                                  "matched_phrases": ["fallback: cheque present"],
                                  "legal_impact": "Establishes core Section 138 NI Act offence."})
            if case_data.get("notice_sent"):
                concepts.append({"concept": "legal_notice_compliance", "confidence": 0.72,
                                  "matched_phrases": ["fallback: notice sent"],
                                  "legal_impact": "Satisfies mandatory notice requirement under S.138(b)."})
            if case_data.get("debt_proven"):
                concepts.append({"concept": "legally_enforceable_debt", "confidence": 0.75,
                                  "matched_phrases": ["fallback: debt proven"],
                                  "legal_impact": "Establishes legally enforceable liability under S.139."})

        logger.debug(f"[JUDIQ] Concepts detected: {[c.get('concept') for c in concepts]}")

        # ── Step 4: Reasoning Layer (each call independently guarded) ──────────
        case_summary = _safe_call(
            ReasoningEngine.summarize_case, case_data,
            fallback="Case summary could not be generated. Please review case details manually.",
            context="ReasoningEngine.summarize_case"
        )
        statutory_interpretation = _safe_call(
            ReasoningEngine.interpret_statutes, case_data, concepts,
            fallback=[],
            context="ReasoningEngine.interpret_statutes"
        )
        precedents = _safe_call(
            ReasoningEngine.match_precedents, concepts,
            fallback=[],
            context="ReasoningEngine.match_precedents"
        )
        reasoning_trail = _safe_call(
            ReasoningEngine.generate_reasoning_trail, case_data, concepts,
            fallback=["Reasoning trail unavailable — engine encountered an error."],
            context="ReasoningEngine.generate_reasoning_trail"
        )

        # ── Step 5: Timeline & Evidence ────────────────────────────────────────
        timeline = _safe_call(
            TimelineEngine.generate_timeline, case_data,
            fallback=[],
            context="TimelineEngine.generate_timeline"
        )
        limitation_result = _safe_call(
            TimelineEngine.check_limitation, case_data,
            fallback={"is_barred": False, "status": "ERROR"},
            context="TimelineEngine.check_limitation"
        )

        evidence = {
            "strength":         "STRONG" if (case_data.get("cheque_present") and case_data.get("dishonour_memo")) else "WEAK",
            "score_multiplier": 1.0      if case_data.get("cheque_present") else 0.8
        }

        # ── Step 6: Scoring ────────────────────────────────────────────────────
        # Pass limitation to scoring
        scoring_result = _safe_call(
            ScoringEngineV12.calculate_score_with_trace, case_data, concepts, [], evidence,
            fallback={"final_score": 0, "score": 0, "verdict": "WEAK", "risk_level": "HIGH",
                      "analysis_confidence": 0, "breakdown": {}},
            context="ScoringEngine"
        )
        final_score = float(scoring_result.get("final_score") or scoring_result.get("score") or 0)

        # ── Step 7: Defence Engine ─────────────────────────────────────────────
        defences = _safe_call(
            DefenceEngineV12.generate_ranked_defences, concepts, case_data, final_score,
            fallback=[],
            context="DefenceEngine"
        )

        # ── Step 8: Decision-Support Layer ────────────────────────────────────
        verdict = "STRONG" if final_score > 70 else ("MODERATE" if final_score > 40 else "WEAK")

        risks_and_rebuttals = _safe_call(
            DecisionSupportEngine.identify_risks_and_rebuttals, concepts, case_data,
            fallback=[],
            context="DecisionSupportEngine.risks"
        )
        outcome_prediction = _safe_call(
            DecisionSupportEngine.predict_outcome, final_score,
            fallback={"prediction": "Unable to determine", "probability": "N/A",
                      "rationale": "Scoring data was insufficient.", "score_band": "WEAK"},
            context="DecisionSupportEngine.predict_outcome"
        )
        translated_verdict = _safe_call(
            DecisionSupportEngine.translate_verdict, verdict, "hindi",
            fallback=verdict,
            context="DecisionSupportEngine.translate_verdict"
        )
        evidence_suggestions = _safe_call(
            DecisionSupportEngine.suggest_evidence_gaps, case_data,
            fallback=[],
            context="DecisionSupportEngine.evidence_gaps"
        )

        # ── Step 9: Draft Generation ───────────────────────────────────────────
        draft_type = _safe_call(
            decide_draft_type, final_score, concepts, case_data,
            fallback="LEGAL_OPINION",
            context="decide_draft_type"
        )
        draft = _safe_call(
            DraftEngine.generate_draft, draft_type, final_score, concepts, case_data,
            fallback="Draft generation encountered an error. Please use the Draft Generator section.",
            context="DraftEngine.generate_draft"
        )

        # ── Step 10: Assemble & Return ─────────────────────────────────────────
        engine_output = {
            **scoring_result,
            "concepts":                  concepts,
            "defences":                  defences,
            "timeline":                  timeline,
            "limitation":                limitation_result,
            "draft":                     draft,
            "draft_type":                draft_type,
            # Reasoning Layer
            "case_summary":              case_summary,
            "statutory_interpretation":  statutory_interpretation,
            "precedents":                precedents,
            "reasoning_trail":           reasoning_trail,
            # Decision-Support Layer
            "risks_and_rebuttals":       risks_and_rebuttals,
            "outcome_prediction":        outcome_prediction,
            "translated_verdict":        translated_verdict,
            "evidence_suggestions":      evidence_suggestions,
        }

        return ResponseBuilder.build_final_response(engine_output, case_data)
