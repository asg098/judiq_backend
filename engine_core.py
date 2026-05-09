import logging
from typing import Dict, List, Any
from datetime import datetime

# ── Logging Configuration ──────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Safe Fallback Builder ──────────────────────────────────────────────────
def _safe_call(fn, *args, fallback, context=""):
    """Call fn(*args); on any exception return fallback and log the error."""
    try:
        return fn(*args)
    except Exception as exc:
        logger.error(f"[ENGINE] {context} failed: {exc}", exc_info=True)
        return fallback

# ── Module Governance Registry ───────────────────────────────────────────
class EngineRegistry:
    """
    Enforces interface discipline and dependency governance.
    Addresses Scalability Governance weakness by decoupling module access.
    """
    def __init__(self):
        # Lazy imports to prevent circular dependency issues
        from scoring_engine   import ScoringEngineV12
        from semantic_engine  import SemanticEngine
        from adversarial_engine import AdversarialEngine
        from strategy_engine  import StrategyEngine
        from draft_engine     import DraftEngine
        from reasoning_engine import ReasoningEngine
        from timeline_engine  import TimelineEngine
        from simulator_engine import SimulatorEngine
        from defence_engine   import DefenceEngineV12
        from decision_support_engine import DecisionSupportEngine

        self.modules = {
            "scoring":     ScoringEngineV12,
            "semantic":    SemanticEngine,
            "adversarial": AdversarialEngine,
            "strategy":    StrategyEngine,
            "draft":       DraftEngine,
            "reasoning":   ReasoningEngine,
            "timeline":    TimelineEngine,
            "simulator":   SimulatorEngine,
            "defence":     DefenceEngineV12,
            "decision":    DecisionSupportEngine
        }

    def get(self, module_name: str):
        if module_name not in self.modules:
            raise ImportError(f"Engine Component '{module_name}' not found in registry.")
        return self.modules[module_name]

# Global Registry Instance
registry = EngineRegistry()

# ── Synthetic Text Mapping (For Quick/Ghost Analysis) ───────────────────────
SYNTHETIC_TEXT_MAP = {
    "cheque_present":  "cheque dishonoured and bounced by bank",
    "dishonour_memo":  "bank issued dishonour memo and return slip",
    "notice_sent":     "legal notice served on accused",
    "debt_proven":     "loan agreement executed and legally enforceable debt established",
}

class JudiQEngine:
    """
    Central orchestrator -- fully fault-tolerant.
    Each pipeline step is independently guarded so a failure in one layer
    NEVER crashes the entire analysis.
    """

    @classmethod
    def analyze_case(cls, raw_data: dict, analysis_mode: str = "detailed") -> dict:
        """
        Hardened Orchestrator - uses EngineRegistry for all sub-module calls.
        """
        from normalizer import normalize_input, validate_minimum_viability, ValidationError
        from response_builder import ResponseBuilder

        # -- 1. Normalization & Validation -----------------------------------
        try:
            validate_minimum_viability(raw_data)
        except ValidationError as e:
            logger.error(f"Validation failed: {e.message}")
            raise

        case_data = normalize_input(raw_data)
        case_data["analysis_mode"] = analysis_mode
        logger.info(f"[JUDIQ] Core analysis triggered for: {case_data.get('case_id', 'ANON')}")

        # -- 2. Semantic Extraction -------------------------------------------
        text = case_data.get("description", "").strip()
        if not text:
            parts = [phrase for key, phrase in SYNTHETIC_TEXT_MAP.items() if case_data.get(key)]
            text = ". ".join(parts)

        semantic_engine = registry.get("semantic")
        semantic_result = _safe_call(
            semantic_engine.analyze_text, text,
            fallback={"concepts_detected": [], "entities": []},
            context="SemanticEngine"
        )
        concepts = semantic_result.get("concepts_detected") or []

        # -- 3. Adversarial Audit ---------------------------------------------
        adversarial_engine = registry.get("adversarial")
        adversarial_result = _safe_call(
            adversarial_engine.audit_case, case_data, concepts,
            fallback={"risks_and_rebuttals": [], "contradictions": []},
            context="AdversarialEngine"
        )
        attack_chains = adversarial_result.get("risks_and_rebuttals", [])
        contradictions = adversarial_result.get("contradictions", [])
        
        # Risk Metric
        adversarial_risk = _safe_call(
            adversarial_engine.calculate_adversarial_risk, attack_chains,
            fallback=0.2,
            context="AdversarialEngine.risk"
        )

        # -- 4. Scoring Engine ------------------------------------------------
        scoring_engine = registry.get("scoring")
        scoring_result = _safe_call(
            scoring_engine.calculate_score_with_trace, case_data, concepts, contradictions, {},
            fallback={"score": 50, "final_score": 50, "reasoning_trace": ["Internal scoring error."]},
            context="ScoringEngine"
        )
        final_score = float(scoring_result.get("final_score") or scoring_result.get("score") or 50)

        # -- 5. Strategic Layer -----------------------------------------------
        strategy_engine = registry.get("strategy")
        strategy_result = _safe_call(
            strategy_engine.generate_strategy if hasattr(strategy_engine, 'generate_strategy') else strategy_engine.generate_litigation_map, 
            case_data, concepts, int(final_score), adversarial_risk,
            fallback={"litigation_strategy": "Maintain standard procedural posture."},
            context="StrategyEngine"
        )

        # -- 6. Reasoning & Traceability (Explainable AI) --------------------
        reasoning_engine = registry.get("reasoning")
        reasoning_trail = _safe_call(
            reasoning_engine.generate_reasoning_trail, case_data, concepts, final_score,
            fallback=[{"text": "Reasoning trail generation failed.", "provenance": "AI_INFERENCE", "confidence": 0.5}],
            context="ReasoningEngine.trail"
        )
        
        case_summary = _safe_call(
            reasoning_engine.summarize_case, case_data,
            fallback="Case assessment based on statutory pillars.",
            context="ReasoningEngine.summary"
        )

        # -- 7. Draft Generation ----------------------------------------------
        draft_engine = registry.get("draft")
        from draft_engine import decide_draft_type
        draft_type = decide_draft_type(int(final_score), concepts, case_data)
        draft_content = _safe_call(
            draft_engine.generate_draft, draft_type, int(final_score), concepts, case_data,
            fallback="Legal draft generation failed. Please use manual templates.",
            context="DraftEngine"
        )

        # -- 8. Decision Support & Intelligence -------------------------------
        decision_engine = registry.get("decision")
        outcome_prediction = _safe_call(
            decision_engine.predict_outcome, final_score,
            fallback={"prediction": "Unknown", "probability": "0%"},
            context="DecisionSupportEngine.outcome"
        )
        translated_verdict = _safe_call(
            decision_engine.translate_verdict, scoring_result.get("verdict", "MODERATE"), case_data.get("target_lang", "hindi"),
            fallback="मजबूत मामला",
            context="DecisionSupportEngine.translate"
        )
        evidence_suggestions = _safe_call(
            decision_engine.suggest_evidence_gaps, case_data,
            fallback=[],
            context="DecisionSupportEngine.evidence"
        )
        decision_risks = _safe_call(
            decision_engine.identify_risks_and_rebuttals, concepts, case_data,
            fallback=[],
            context="DecisionSupportEngine.risks"
        )
        
        # Merge risks from both engines
        if "risks_and_rebuttals" not in adversarial_result:
            adversarial_result["risks_and_rebuttals"] = []
            
        existing_risk_titles = {r.get("attack_vector", r.get("risk")) for r in adversarial_result["risks_and_rebuttals"]}
        for dr in decision_risks:
            if dr["risk"] not in existing_risk_titles:
                adversarial_result["risks_and_rebuttals"].append({
                    "attack_vector": dr["risk"],
                    "tactical_chain": [dr["description"]],
                    "survival_probability": "65%",
                    "destruction_probability": "35%",
                    "rebuttal_tree": {
                        "complainant_counter": dr["rebuttal"],
                        "magistrate_view": f"High attention to {dr['case_law']}"
                    }
                })

        # -- 9. Timeline & Simulation -----------------------------------------
        timeline_engine = registry.get("timeline")
        timeline = _safe_call(
            timeline_engine.generate_timeline, case_data,
            fallback=[],
            context="TimelineEngine.generate"
        )
        limitation = _safe_call(
            timeline_engine.check_limitation, case_data,
            fallback={"is_barred": False, "status": "CALCULATION_ERROR"},
            context="TimelineEngine.limitation"
        )

        # -- 10. Response Assembly ---------------------------------------------
        # Prepare the flat dict for ResponseBuilder
        engine_output = {
            "final_score": final_score,
            "reasoning_trace": scoring_result.get("reasoning_trace", []),
            "score_breakdown": scoring_result.get("breakdown", {}),
            "concepts": concepts,
            "adversarial_result": adversarial_result,
            "outcome_prediction": outcome_prediction,
            "translated_verdict": translated_verdict,
            "evidence_suggestions": evidence_suggestions,
            "reasoning_trail": reasoning_trail,
            "case_summary": case_summary,
            "draft": draft_content,
            "draft_type": draft_type,
            "timeline": timeline,
            "limitation": limitation,
            "strategy_result": strategy_result,
            "adversarial_risk": adversarial_risk
        }

        # Merge results into the structure ResponseBuilder expects
        full_result = {**engine_output, **scoring_result}
        
        return ResponseBuilder.build_final_response(full_result, case_data)