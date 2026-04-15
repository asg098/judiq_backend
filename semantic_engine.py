import re
import logging
from typing import List, Dict, Any, Tuple
from kb_manager import kb_manager

logger = logging.getLogger(__name__)

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

class SemanticEngineV12:
    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, Any]:
        detected = cls.detect_concepts(text)
        return {
            "concepts_detected": detected,
            "total_confidence": (
                sum(c.get("confidence", 0) for c in detected) / len(detected)
                if detected else 0.0
            ),
            "count": len(detected),
            "method": "SemanticEngineV12_unified",
            "text_analyzed": text[:200] + "..." if len(text) > 200 else text,
        }

    @classmethod
    def detect_concepts(cls, text: str) -> List[Dict]:
        if not text:
            return []
        text_lower = text.lower()
        detected = []
        concepts_config = kb_manager.get_legal_concepts()
        for concept, config in concepts_config.items():
            matched_phrases = []
            match_count = 0
            patterns = config.get('patterns', [])
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    match_count += 1
                    for match in ensure_list(matches):
                        if isinstance(match, tuple):
                            matched_phrases.append(match[0] if match[0] else str(match))
                        else:
                            matched_phrases.append(match)
            if match_count > 0:
                base_confidence = min(match_count / len(patterns), 1.0) if patterns else 0.5
                weight_adjusted = base_confidence * config.get('weight', 1.0)
                phrase_boost = min(len(set(matched_phrases)) * 0.1, 0.2)
                final_confidence = min(weight_adjusted + phrase_boost, 1.0)
                detected.append({
                    "concept": concept,
                    "confidence": round(final_confidence, 2),
                    "matched_phrases": list(set(matched_phrases))[:5],
                    "legal_impact": config.get('legal_impact', "N/A")
                })
        detected.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return detected

class EnhancedSemanticExtractor:
    @staticmethod
    def extract_concepts(text: str, threshold: float = 0.25) -> Dict[str, Any]:
        result = SemanticEngineV12.analyze_text(text)
        concepts = result.get("concepts_detected", [])
        filtered = [c for c in concepts if c.get("confidence", 0) >= threshold]
        return {
            "concepts_detected": filtered,
            "total_confidence": (
                sum(c.get("confidence", 0) for c in filtered) / len(filtered)
                if filtered else 0.0
            ),
            "count": len(filtered),
            "method": "SemanticEngineV12_unified_compat",
            "text_analyzed": result.get("text_analyzed", "")
        }
