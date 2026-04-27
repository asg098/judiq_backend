import logging
logger = logging.getLogger(__name__)

# -- Synthetic text map -------------------------------------------------------
SYNTHETIC_TEXT_MAP = {
    "cheque_present":  "cheque dishonoured and bounced by bank",
    "dishonour_memo":  "bank issued dishonour memo and return slip",
    "notice_sent":     "legal notice served on accused",
    "debt_proven":     "loan agreement executed and legally enforceable debt established",
}

# -- Structural negative signals ----------------------------------------------
STRUCTURAL_NEGATIVE_CONCEPTS = {
    "debt_proven": {
        "concept": "no_debt_proof",
        "confidence": 0.72,
        "matched_phrases": ["debt not proven -- structural signal"],
        "legal_impact": "Challenges legal enforceability under S.139."
    },
    "notice_sent": {
        "concept": "notice_defect",
        "confidence": 0.88,
        "matched_phrases": ["notice not sent -- structural signal"],
        "legal_impact": "Mandatory requirement under S.138(b)."
    },
}

# -- Safe fallback builders ---------------------------------------------------

def _safe_call(fn, *args, fallback, context=""):
    """Call fn(*args); on any exception return fallback and log the error."""
    try:
        return fn(*args)
    except Exception as exc:
        logger.error(f"[ENGINE] {context} failed: {exc}", exc_info=True)
        return fallback


class JudiQEngine:
    """
    Central orchestrator -- fully fault-tolerant.
    Each pipeline step is independently guarded so a failure in one layer
    NEVER crashes the entire analysis.
    """

    @classmethod
    def analyze_case(cls, raw_data: dict) -> dict:
        from semantic_engine  import SemanticEngineV12
        from scoring_engine   import ScoringEngineV12

        # -- Robust aliased imports -------------------------------------------
        try:
            from defence_engine import DefenceEngineV12
        except ImportError:
            class DefenceEngineV12:
                @staticmethod
                def analyze_defences(c): return {"score": 0, "found": []}
            logger.warning("Defence Engine NOT found -- using fallback.")

        try:
            from decision_support_engine import DecisionSupportEngine
        except ImportError:
            class DecisionSupportEngine:
                @staticmethod
                def analyze_risks(c): return []
            logger.warning("Decision Support Engine NOT found -- using fallback.")
        # ---------------------------------------------------------------------

        from timeline_engine  import TimelineEngine
        from draft_engine     import DraftEngine, decide_draft_type
        from response_builder import ResponseBuilder
        from normalizer       import normalize_input, validate_minimum_viability, ValidationError
        from reasoning_engine import ReasoningEngine
        from simulator_engine import SimulatorEngine

        # -- Hard gate --------------------------------------------------------
        validate_minimum_viability(raw_data)

        # -- Step 1: Normalise ------------------------------------------------
        case_data = normalize_input(raw_data)
        logger.info(f"[JUDIQ] Analyzing case: {case_data.get('case_id', 'ANON')}")

        # -- Step 2: Semantic analysis ----------------------------------------
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

        # -- Step 3: Inject structural negative signals -----------------------
        for pillar_key, signal in STRUCTURAL_NEGATIVE_CONCEPTS.items():
            if not case_data.get(pillar_key) and signal["concept"] not in existing_concepts:
                concepts.append(dict(signal))
                existing_concepts.add(signal["concept"])

        # Positive fallback -- only if nothing at all was detected
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
        
        # -- Step 3.2: Financial Capacity Logic (Expert Hardening) -------------
        # If high amount cash loan without ITR/Bank proof
        amt = float(case_data.get("amount") or 0)
        if amt > 150000 and not case_data.get("loan_via_bank") and not case_data.get("complainant_itr_available"):
            if "financial_capacity_risk" not in existing_concepts:
                concepts.append({
                    "concept": "financial_capacity_risk",
                    "confidence": 0.82,
                    "matched_phrases": ["Inherent financial capacity risk for cash loans"],
                    "legal_impact": "Basalingappa v. Mudibasappa rule: Complainant's source of funds can be challenged."
                })
                existing_concepts.add("financial_capacity_risk")

        # -- Step 3.5: Mandatory Litigation Risk Injection (Enemy Audit Fix) --
        # No case is zero-risk. Every S.138 case carries inherent trial risk.
        concepts.append({
            "concept": "litigation_risk",
            "confidence": 0.52,
            "matched_phrases": ["Inherent trial risk -- mandatory audit signal"],
            "legal_impact": "Standard procedural risk, judicial discretion, and potential litigation delays."
        })

        logger.debug(f"[JUDIQ] Concepts detected: {[c.get('concept') for c in concepts]}")

        # -- Step 6: Scoring & Compliance Scorecard --------------------------
        score_data = _safe_call(
            ScoringEngineV12.calculate_score_with_trace,
            case_data, concepts, [], {},
            fallback={"score": 50, "compliance_pct": 50, "breakdown": {}},
            context="ScoringEngine"
        )
        final_score = score_data.get("score", 50)
        compliance_scorecard = {
            "percentage": score_data.get("compliance_pct", 50),
            "breakdown": score_data.get("breakdown", {})
        }
        
        # -- Step 7: Reasoning & Precedent Match -----------------------------
        case_summary = _safe_call(
            ReasoningEngine.generate_case_summary, concepts, final_score,
            fallback="Standard legal analysis summary.",
            context="ReasoningEngine.summary"
        )
        
        precedents = _safe_call(
            ReasoningEngine.find_relevant_precedents, concepts,
            fallback=[],
            context="ReasoningEngine.precedents"
        )
        
        # Proof Presence Auto-Check
        proof_card = {
            "status": "VALIDATED" if case_data.get("proof_present", True) else "MISSING",
            "detected_docs": [k for k,v in case_data.items() if v is True and k in ["cheque_present", "dishonour_memo", "notice_sent", "debt_proven"]]
        }
        
        # Client Friendly Summary
        client_summary = _safe_call(
            ReasoningEngine.generate_client_summary, {"score": final_score, "concepts": concepts},
            fallback="Analysis complete. Review documents for details.",
            context="ReasoningEngine.client_summary"
        )
        
        # Conviction Probability Trend
        probability_trend = _safe_call(
            ReasoningEngine.determine_trend, final_score,
            fallback="STABLE",
            context="ReasoningEngine.trend"
        )
        reasoning_trail = _safe_call(
            ReasoningEngine.generate_reasoning_trail, case_data, concepts,
            fallback=["Engine encountered non-fatal reasoning bottleneck."],
            context="ReasoningEngine.trail"
        )

        if evidence_score >= 5: evidence_strength = "STRONG"
        elif evidence_score <= 1: evidence_strength = "WEAK"

        evidence_assessment = {
            "strength": evidence_strength,
            "gaps": []
        }

        scoring_result = _safe_call(
            ScoringEngineV12.calculate_score_with_trace,
            case_data, concepts, [], evidence_assessment,
            fallback={"final_score": 0, "reasoning_trace": ["Scoring failed due to internal error."]},
            context="ScoringEngine"
        )
        final_score = float(scoring_result.get("final_score") or scoring_result.get("score") or 0)

        # -- Step 7: Defence Engine -------------------------------------------
        defences = _safe_call(
            DefenceEngineV12.generate_ranked_defences, concepts, case_data, final_score,
            fallback=[],
            context="DefenceEngine"
        )

        # -- Step 8: Decision-Support Layer ------------------------------------
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
        
        # -- Step 8.5: Litigation Strategy Map (Expert Hardening) -------------
        from strategy_engine import StrategyEngine
        litigation_strategy = _safe_call(
            StrategyEngine.generate_litigation_map, case_data, final_score, concepts,
            fallback={"prosecution_map": {}, "defence_map": {}, "overall_strategy": "Standard"},
            context="StrategyEngine"
        )

        # -- Step 9: Draft Engine ---------------------------------------------
        draft_type = _safe_call(
            decide_draft_type, int(final_score), concepts, case_data,
            fallback="LEGAL_OPINION",
            context="DraftTypeDecider"
        )
        draft_content = _safe_call(
            DraftEngine.generate_draft, draft_type, int(final_score), concepts, case_data,
            fallback="Legal draft generation failed. Please use manual templates.",
            context="DraftEngine"
        )
        
        # -- Step 9.5: Cross-Examination Simulator -----------------------------
        cross_exam_prep = _safe_call(
            SimulatorEngine.generate_simulation, concepts, float(case_data.get("amount") or 0),
            fallback=[],
            context="SimulatorEngine"
        )

        # -- Step 10: Final Response Assembly ---------------------------------
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
            "case_summary":             case_summary,      # was missing — causes empty output
            "draft":                    draft_content,
            "draft_type":               draft_type,
            "evidence_suggestions":     evidence_suggestions,
            "litigation_strategy":      litigation_strategy,
            "compliance_scorecard":     compliance_scorecard,
            "timeline_visualizer":      timeline_visualizer,
            "proof_card":               proof_card,
            "client_summary":           client_summary,
            "probability_trend":        probability_trend,
            "closest_precedent":        precedents[0] if precedents else None,
            "analysis_mode":            case_data.get("analysis_mode", "detailed"),
            "proof_present":            case_data.get("proof_present", True),
            "cross_exam_prep":          cross_exam_prep,
            "cri_score":                score_data.get("cri_score", 0)
        }

        return ResponseBuilder.build_final_response(engine_result, case_data)