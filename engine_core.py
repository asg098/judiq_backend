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
        from semantic_engine  import SemanticEngineV12
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
            "semantic":    SemanticEngineV12,
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
        
        # NEW: Contradiction Engine
        contradictions = _safe_call(
            adversarial_engine.detect_contradictions, case_data, concepts,
            fallback=[],
            context="ContradictionEngine"
        )
        
        # NEW: Timeline Anomaly Detector
        timeline_anomalies = _safe_call(
            adversarial_engine.detect_timeline_anomalies, case_data,
            fallback=[],
            context="TimelineAnomalyDetector"
        )
        
        # Risk Metric
        adversarial_risk = _safe_call(
            adversarial_engine.calculate_adversarial_risk, attack_chains,
            fallback=0.2,
            context="AdversarialEngine.risk"
        )

        evidence_dependencies = _safe_call(
            adversarial_engine.map_evidence_dependencies, case_data,
            fallback=[],
            context="EvidenceDependencyMapping"
        )

        # NEW: Strategic Audit
        red_team_attacks = _safe_call(
            adversarial_engine.run_strategic_audit, case_data, concepts,
            fallback=[],
            context="StrategicAudit"
        )
        
        # NEW: Witness Pressure Simulation
        witness_pressure = _safe_call(
            adversarial_engine.simulate_witness_pressure, case_data, adversarial_risk,
            fallback={},
            context="WitnessPressure"
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
        
        # NEW: Causal Story Flow
        causal_story = _safe_call(
            reasoning_engine.generate_causal_story, case_data, concepts,
            fallback=[],
            context="CausalStoryBuilder"
        )

        # -- 10. Reasoning Trail (Provenance & Explainability) ----------------
        reasoning_trail = _safe_call(
            reasoning_engine.generate_reasoning_trail, 
            case_data, 
            semantic_result.get("concepts_detected", []), 
            scoring_result.get("score", 0),
            scoring_result, # Pass calibrated result
            fallback=[],
            context="Reasoning Trail"
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

        logger.info(f"DRAFT_ENGINE: Type={draft_type}, Size={len(draft_content) if draft_content else 0}")
        
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
        
        # -- 8. Integrated Adversarial Analysis -------------------------------
        # Merge risks from both engines with Deduplication (Contextual Severity Engine)
        if "risks_and_rebuttals" not in adversarial_result:
            adversarial_result["risks_and_rebuttals"] = []
            
        existing_risk_titles = {str(r.get("adversarial_vector", r.get("risk", ""))).lower() for r in adversarial_result["risks_and_rebuttals"]}
        
        for dr in decision_risks:
            dr_title = str(dr["risk"]).lower()
            if dr_title not in existing_risk_titles:
                existing_risk_titles.add(dr_title)
                adversarial_result["risks_and_rebuttals"].append({
                    "adversarial_vector": dr["risk"],
                    "strategic_chain": [dr["description"]],
                    "survival_probability": "65%",
                    "collapse_risk": "35%",
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

        # -- 10. Executive TL;DR Layer (New) ----------------------------------
        # Fulfills User Request: Executive-first UX for busy lawyers
        tldr = {
            "core_risk": "Procedural Technicality" if final_score < 40 else ("Evidentiary Gap" if final_score < 70 else "Minimal"),
            "top_threat": adversarial_result["risks_and_rebuttals"][0]["adversarial_vector"] if adversarial_result["risks_and_rebuttals"] else "None identified",
            "best_move": scoring_result.get("remediation_roadmap", [{"action": "Maintain posture"}])[0]["action"],
            "confidence": f"{int(final_score)}%",
            "one_liner": f"Case is {outcome_prediction.get('prediction', 'stable')} with {len(contradictions)} logical inconsistencies detected."
        }

        # -- 11. Response Assembly ---------------------------------------------
        # Prepare the flat dict for ResponseBuilder
        engine_output = {
            "final_score": final_score,
            "tldr": tldr,
            "reasoning_trace": scoring_result.get("reasoning_trace", []),
            "reasoning_trail": reasoning_trail,
            "causal_story": causal_story,
            "contradictions": contradictions,
            "timeline_anomalies": timeline_anomalies,
            "evidence_dependencies": evidence_dependencies,
            "strategic_audit": red_team_attacks,
            "witness_pressure": witness_pressure,
            "uncertainty_intelligence": scoring_result.get("uncertainty_intelligence", []),
            "judicial_mode": scoring_result.get("judicial_mode", "Balanced"),
            "self_challenge": scoring_result.get("self_challenge", {}),
            "reliability_matrix": scoring_result.get("reliability_matrix", {}),
            "case_similarity": scoring_result.get("case_similarity", {}),
            "score_breakdown": scoring_result.get("breakdown", {}),
            "concepts": concepts,
            "adversarial_result": adversarial_result,
            "outcome_prediction": outcome_prediction,
            "translated_verdict": translated_verdict,
            "evidence_suggestions": evidence_suggestions,
            "case_summary": case_summary,
            "draft": draft_content,
            "draft_type": draft_type,
            "timeline": timeline,
            "limitation": limitation,
            "strategy_result": strategy_result,
            "adversarial_risk": adversarial_risk
        }

        # Merge results into the structure ResponseBuilder expects
        full_result = {**engine_output, **scoring_result, **adversarial_result}
        
        return ResponseBuilder.build_final_response(full_result, case_data)
