from typing import List, Dict
from kb_manager import kb_manager

def ensure_list(x):
    if x is None: return []
    if isinstance(x, list): return x
    return [x]

def ensure_dict(x):
    if x is None: return {}
    if isinstance(x, dict): return x
    return {}

def ensure_number(x, default=0):
    try: return float(x)
    except: return default

class DefenceEngineV12:
    @classmethod
    def generate_ranked_defences(cls,
                                 concepts: List[Dict],
                                 case_data: Dict,
                                 case_strength: float) -> List[Dict]:
        defences = []
        weights = kb_manager.get_defence_legal_weights()
        templates = kb_manager.get_defence_templates()
        seen = set()
        for concept_det in ensure_list(concepts):
            concept = concept_det.get("concept", "unknown")
            confidence = ensure_number(concept_det.get("confidence", 0))
            if concept not in templates or concept in seen:
                continue
            if confidence < 0.20:
                continue
            seen.add(concept)
            legal_weight = weights.get(concept, 0.75)
            arg, reb, basis = templates[concept]
            base_prob = confidence * legal_weight * 100
            strength_factor = max(0.5, 1.0 - (case_strength / 200))
            prob = int(base_prob * strength_factor)
            prob = max(10, min(95, prob))
            strength = "LOW"
            if prob >= 70: strength = "HIGH"
            elif prob >= 40: strength = "MEDIUM"
            defences.append({
                "argument": arg,
                "strength": strength,
                "success_probability": prob,
                "trigger_reason": f"{concept.replace('_', ' ')} detected (conf: {confidence:.2f})",
                "rebuttal": reb,
                "legal_basis": basis
            })
        defences.sort(key=lambda x: x['success_probability'], reverse=True)
        return defences
