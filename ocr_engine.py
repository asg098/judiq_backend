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
    def extract_dates(cls, text: str) -> List[str]:
        # Basic regex to catch DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        date_pattern = r'\b(\d{1,2}[-./]\d{1,2}[-./]\d{2,4})\b'
        dates = re.findall(date_pattern, text)
        return list(set(dates))

    @classmethod
    def extract_amounts(cls, text: str) -> List[str]:
        # Regex to catch amounts with Rs, INR, ₹
        amount_pattern = r'(?i)(?:rs\.?|inr|₹|rupees)\s*([\d,]+(?:\.\d{1,2})?)'
        amounts = re.findall(amount_pattern, text)
        return list(set([a.replace(',', '') for a in amounts]))

    @classmethod
    def analyze_document(cls, extracted_text: str, doc_type: str, user_claimed_reason: str = "") -> Dict[str, Any]:
        """
        Extracts key evidence metrics (Dates, Amounts, Reasons) based on document type.
        """
        result = {
            "is_verified": False,
            "detected_reasons": [],
            "extracted_dates": cls.extract_dates(extracted_text),
            "extracted_amounts": cls.extract_amounts(extracted_text),
            "warning": None,
            "verification_confidence": 0.0,
            "extracted_snippet": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
        }

        if doc_type.upper() == "MEMO":
            detected = cls.extract_dishonour_reason(extracted_text)
            result["detected_reasons"] = detected
            
            if not detected:
                result["warning"] = "EVIDENCE GAP: No recognizable bank return code found in the uploaded document."
                result["verification_confidence"] = 0.20
            elif user_claimed_reason and user_claimed_reason in detected:
                result["is_verified"] = True
                result["verification_confidence"] = 0.95
            elif user_claimed_reason:
                result["warning"] = f"DISCREPANCY: The uploaded memo suggests '{detected[0]}', but you selected '{user_claimed_reason}'."
                result["verification_confidence"] = 0.40
            else:
                result["is_verified"] = True
                result["verification_confidence"] = 0.80

        elif doc_type.upper() == "CHEQUE":
            if result["extracted_amounts"]:
                result["is_verified"] = True
                result["verification_confidence"] = 0.85
            else:
                result["warning"] = "EVIDENCE GAP: Could not extract cheque amount from the uploaded document."
                result["verification_confidence"] = 0.30
                
        elif doc_type.upper() == "NOTICE":
            if result["extracted_dates"]:
                result["is_verified"] = True
                result["verification_confidence"] = 0.85
            else:
                result["warning"] = "EVIDENCE GAP: Could not extract dispatch dates from the legal notice."
                result["verification_confidence"] = 0.30

        else:
            result["is_verified"] = len(extracted_text.strip()) > 10
            result["verification_confidence"] = 0.50

        return result

