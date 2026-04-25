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
        from semantic_engine  import SemanticEngineV12
        from scoring_engine   import ScoringEngineV12
        
        # ── Robust aliased imports ──────────────────────────────────────────
        try:
            from defence_engine import DefenceEngineV12
        except ImportError:
            try:
                from defence_support_engine import DefenceEngineV12
            except ImportError:
                # Mock fallback if totally missing
                class DefenceEngineV12:
                    @staticmethod
                    def analyze_defences(c): return {"score": 0, "found": []}
                logger.warning("Defence Engine NOT found — using fallback.")

        try:
            from decision_support_engine import DecisionSupportEngine
        except ImportError:
            try:
                from decesion_support import DecisionSupportEngine
            except ImportError:
                class DecisionSupportEngine:
                    @staticmethod
                    def analyze_risks(c): return []
                logger.warning("Decision Support Engine NOT found — using fallback.")
        # ────────────────────────────────────────────────────────────────────

        from timeline_engine  import TimelineEngine
        from draft_engine     import DraftEngine, decide_draft_type
        from response_builder import ResponseBuilder
        from normalizer       import normalize_input, validate_minimum_viability, ValidationError
        from reasoning_engine import ReasoningEngine

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
            context="ReasoningEngine.statutes"
        )
        precedents = _safe_call(
            ReasoningEngine.match_precedents, concepts,
            fallback=[],
            context="ReasoningEngine.precedents"
        )
        reasoning_trail = _safe_call(
            ReasoningEngine.generate_reasoning_trail, case_data, concepts,
            fallback=["Engine encountered non-fatal reasoning bottleneck."],
            context="ReasoningEngine.trail"
        )

        # ── Step 5: Timeline Analysis ──────────────────────────────────────────
        timeline = _safe_call(
            TimelineEngine.generate_timeline, case_data,
            fallback=[],
            context="TimelineEngine"
        )

        # ── Step 6: Scoring Engine ─────────────────────────────────────────────
        evidence_assessment = {
            "strength": "STRONG" if case_data.get("debt_proven") else "MODERATE",
            "gaps": []
        }
        
        scoring_result = _safe_call(
            ScoringEngineV12.calculate_score_with_trace, 
            case_data, concepts, [], evidence_assessment,
            fallback={"final_score": 0, "reasoning_trace": ["Scoring failed due to internal error."]},
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
            context="DecisionSupportEngine.evidence"
        )

        # ── Step 9: Draft Engine ──────────────────────────────────────────────
        draft_type = decide_draft_type(int(final_score), concepts, case_data)
        try:
            draft_content = DraftEngine.generate_draft(draft_type, int(final_score), concepts, case_data)
        except Exception as exc:
            logger.error(f"[ENGINE] DraftEngine failed: {exc}", exc_info=True)
            draft_content = "Legal draft generation failed. Please use manual templates."

        # ── Step 10: Final Response Assembly ──────────────────────────────────
        engine_result = {
            "final_score":              final_score,
            "reasoning_trace":          scoring_result.get("reasoning_trace", []),
            "score_breakdown":          scoring_result.get("score_breakdown", []),
            "discretionary_caveats":    scoring_result.get("discretionary_caveats", []),
            "concepts":                 concepts,
            "defences":                 defences,
            "risks_and_rebuttals":      risks_and_rebuttals,
            "outcome_prediction":       outcome_prediction,
            "translated_verdict":       translated_verdict,
            "statutory_interpretation": statutory_interpretation,
            "precedents":               precedents,
            "timeline":                 timeline,
            "reasoning_trail":          reasoning_trail,
            "draft":                    draft_content,
            "draft_type":               draft_type,
            "evidence_suggestions":     evidence_suggestions
        }
        
        return ResponseBuilder.build_final_response(engine_result, case_data)
