import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class OCREngine:
    """
    Evidence Sanity Check — OCR Verification for Bank Memos and Cheques.
    This module identifies legal 'Reasons for Return' from bank documents
    to ensure user input matches the physical evidence.
    """
    
    # Mapping of standard banking terms to JudiQ's internal reasons
    REASON_MAP = {
        "Insufficient Funds": [
            "funds insufficient", "insufficient funds", "shortage", 
            "exceeds arrangement", "bal. insufficient", "short of funds"
        ],
        "Account Closed": [
            "account closed", "a/c closed", "closed"
        ],
        "Payment Stopped": [
            "payment stopped", "stopped by drawer", "stop payment", 
            "payment stopped by drawer"
        ],
        "Signature Mismatch": [
            "signature mismatch", "signature differs", "differs", 
            "drawers signature differs"
        ],
        "Refer to Drawer": [
            "refer to drawer", "r.t.d.", "contact drawer"
        ],
        "Frozen Account": [
            "account frozen", "frozen", "attached by order", "garnishee"
        ],
        "Exceed Arrangement": [
            "exceeds arrangement", "limit exceeded"
        ]
    }

    @classmethod
    def extract_dishonour_reason(cls, text: str) -> List[str]:
        """
        Scans extracted text for legal dishonour reasons.
        """
        text_lower = text.lower()
        found = []
        for reason, keywords in cls.REASON_MAP.items():
            for kw in keywords:
                if kw in text_lower:
                    found.append(reason)
                    break
        return found

    @classmethod
    def verify_evidence_consistency(cls, extracted_text: str, user_claimed_reason: str) -> Dict[str, Any]:
        """
        Cross-references OCR text against the user's wizard selection.
        """
        detected = cls.extract_dishonour_reason(extracted_text)
        
        is_verified = False
        warning = None
        confidence = 0.0

        if not detected:
            warning = "EVIDENCE GAP: No recognizable bank return code found in the uploaded document."
            confidence = 0.20
        elif user_claimed_reason in detected:
            is_verified = True
            confidence = 0.95
        else:
            warning = f"DISCREPANCY: The uploaded memo suggests '{detected[0]}', but you selected '{user_claimed_reason}'."
            confidence = 0.40

        return {
            "is_verified": is_verified,
            "detected_reasons": detected,
            "warning": warning,
            "verification_confidence": confidence,
            "extracted_snippet": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
        }
