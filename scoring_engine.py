import logging
import hashlib
from typing import List, Dict, Any
from kb_manager import kb_manager

logger = logging.getLogger(__name__)

def ensure_list(x):
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def ensure_dict(x):
    if x is None: return {}
    if isinstance(x, dict): return x
    return x

def ensure_number(x, default=0):
    try: return float(x)
    except: return default

class ScoringEngineV12:
    @classmethod
    def resolve_conflicts(cls, concepts: List[Dict]) -> List[Dict]:
        concept_names = [c["concept"] for c in concepts]
        resolved = []
        conflicts = [
            ("legally_enforceable_debt", "no_debt_proof"),
            ("legal_notice_compliance", "notice_defect"),
            ("cheque_bounce", "dishonour_disputed")
        ]
        conf_map = {c["concept"]: c["confidence"] for c in concepts}
        blacklisted = set()
        for pos, neg in conflicts:
            if pos in concept_names and neg in concept_names:
                if conf_map[pos] > conf_map[neg] + 0.1:
                    blacklisted.add(neg)
                else:
                    blacklisted.add(pos)
        for c in concepts:
            if c["concept"] not in blacklisted:
                resolved.append(c)
        return resolved

    @classmethod
    def calculate_score_with_trace(cls, 
                                   case_data: Dict,
                                   concepts: List[Dict],
                                   contradictions: List[Dict],
                                   evidence_assessment: Dict) -> Dict:
        concepts = cls.resolve_conflicts(ensure_list(concepts))
        trace = []
        base_score = 35
        score = base_score
        fatal_conditions = []
        case_id = str(case_data.get("case_id", "DEFAULT_ID"))
        trace.append(f"Base score: {base_score}")
        cheque = bool(case_data.get('cheque_present'))
        memo = bool(case_data.get('dishonour_memo'))
        notice = bool(case_data.get('notice_sent'))
        debt = bool(case_data.get('debt_proven'))
        if cheque: 
            score += 10
            trace.append("+10 instrument present")
        else: 
            score -= 25
            trace.append("-25 instrument missing")
        if memo: 
            score += 10
            trace.append("+10 memo available")
        if notice: 
            score += 8
            trace.append("+8 notice compliance")
        else: 
            score -= 30
            trace.append("-30 notice defect (fatal)")
        if debt:
            proof_method = case_data.get("debt_proof_type", "written_agreement").lower()
            impact = 12 if proof_method != "verbal" else 4
            score += impact
            trace.append(f"+{impact} debt provenance ({proof_method})")
        else:
            score -= 35
            trace.append("-35 debt not established")
        if cheque and memo and notice and debt:
            synergy = 5
            score += synergy
            trace.append(f"+5 strong case synergy bonus")
        catalogue = kb_manager.get_scoring_catalogue()
        score_breakdown = []
        positive_concepts = [
            "legally_enforceable_debt",
            "legal_notice_compliance",
            "strong_documentary_evidence",
            "cheque_bounce"
        ]
        for concept_det in concepts:
            concept = concept_det.get("concept", "unknown")
            confidence = ensure_number(concept_det.get("confidence", 0))
            if confidence < 0.2:
                continue
            if concept in positive_concepts:
                boost = int((confidence ** 2) * 10)
                score += boost
                trace.append(f"+{boost} {concept} strength boost")
                score_breakdown.append(f"{concept} (+{boost})")
                continue
            
            lookup_concept = concept
            if lookup_concept not in catalogue:
                alias = "signature_dispute" if concept == "signature_disputed" else ("signature_disputed" if concept == "signature_dispute" else None)
                if alias and alias in catalogue:
                    lookup_concept = alias
                else:
                    continue
            base_penalty, legal_weight, _ = catalogue[lookup_concept]
            
            if confidence < 0.5:
                penalty_multiplier = 0.5
                impact_factor = confidence
            else:
                penalty_multiplier = 1.0
                impact_factor = confidence ** 2
            
            scaled_penalty = int(impact_factor * legal_weight * base_penalty * 0.6 * penalty_multiplier)
            score += scaled_penalty
            trace.append(f"{scaled_penalty:+d} {concept} (conf: {confidence:.2f})")
            score_breakdown.append(f"{concept} ({scaled_penalty})")
            risk = kb_manager.get_risk_level(concept)
            if risk == "CRITICAL" and confidence >= 0.75:
                fatal_conditions.append(concept)
        variation_hash = int(hashlib.md5(case_id.encode()).hexdigest(), 16)
        variation = variation_hash % 12
        score += variation
        score = max(0, min(score, 100))
        return {
            "final_score": score,
            "reasoning_trace": trace,
            "score_breakdown": score_breakdown or ["Clean analysis logic applied"]
        }
