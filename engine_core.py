from semantic_engine import SemanticEngineV12
from scoring_engine import ScoringEngineV12
from defence_engine import DefenceEngineV12
from timeline_engine import TimelineEngine
from draft_engine import DraftEngine
from response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)

class JudiQEngine:
    @classmethod
    def analyze_case(cls, case_data: dict):
        description = case_data.get("description", "")
        semantic_result = SemanticEngineV12.analyze_text(description)
        concepts = semantic_result.get("concepts_detected", [])
        timeline = TimelineEngine.generate_timeline(case_data)
        limitation = TimelineEngine.check_limitation(case_data)
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
        draft = DraftEngine.generate_opinion({**scoring_result, "verdict": "TBD"})
        engine_output = {
            **scoring_result,
            "concepts": concepts,
            "defences": defences,
            "timeline": timeline,
            "draft": draft
        }
        return ResponseBuilder.build_final_response(engine_output, case_data)
