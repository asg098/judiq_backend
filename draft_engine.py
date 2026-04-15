import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

SECTION_REFS = {
    "notice_defect":           "S.138(b) NI Act — Statutory notice is mandatory; defect is fatal to prosecution.",
    "no_debt_proof":           "S.139 NI Act — Legally enforceable debt must exist; presumption is rebuttable.",
    "signature_dispute":       "S.118 NI Act — Burden on complainant to establish genuineness of signature.",
    "security_cheque":         "S.139 NI Act — Cheques given as security fall outside the scope of S.138.",
    "limitation_issue":        "S.142(b) NI Act — Complaint must be filed within 1 month of cause of action.",
    "cheque_misuse":           "S.138 NI Act — Cheque must be drawn for the specific liability claimed.",
    "legal_notice_compliance": "S.138(b) NI Act — Statutory demand notice properly served within 30 days.",
    "cheque_bounce":           "S.138 NI Act — Dishonour of cheque establishes the primary offence.",
    "legally_enforceable_debt":"S.139 NI Act — Legally enforceable debt or liability is established.",
    "payment_already_made":    "S.139 NI Act — Prior payment may discharge liability if proven with evidence.",
}

RISK_LABELS = {
    "notice_defect":     "CRITICAL — Procedural bar to prosecution",
    "limitation_issue":  "CRITICAL — Jurisdictional bar",
    "signature_dispute": "HIGH — Challenges instrument authenticity",
    "security_cheque":   "HIGH — May eliminate S.138 liability entirely",
    "no_debt_proof":     "HIGH — Weakens evidentiary presumption",
    "cheque_misuse":     "MEDIUM — Questions legitimate purpose of instrument",
    "payment_already_made": "MEDIUM — Discharge of liability defense",
}

class DraftEngine:
    @staticmethod
    def generate_opinion(analysis_result: Dict[str, Any]) -> str:
        score = analysis_result.get("score", 0)
        verdict = analysis_result.get("verdict", "Unknown")
        concepts = analysis_result.get("concepts", [])
        case_data = analysis_result.get("case_data", {})

        if score >= 75:
            strength_narrative = (
                "The case presents a strong evidentiary foundation. All primary conditions under "
                "Section 138 of the Negotiable Instruments Act, 1881 appear to be satisfied. "
                "The complainant is well-positioned to proceed with prosecution."
            )
            recommendation = (
                "RECOMMENDATION: Proceed with filing of complaint before the jurisdictional Magistrate. "
                "Ensure all original documents (cheque, dishonour memo, postal acknowledgment, agreement) "
                "are in possession. Organize a clear timeline from dishonour to notice to filing."
            )
        elif score >= 50:
            strength_narrative = (
                "The case has moderate legal strength but exhibits identifiable defects or risk factors. "
                "While foundational elements may be present, the opposing counsel is likely to raise "
                "targeted defences. Careful pre-litigation preparation is essential."
            )
            recommendation = (
                "RECOMMENDATION: Address identified weaknesses before filing. Obtain additional corroborating "
                "evidence (bank statements, correspondence, witness affidavits). Evaluate whether a pre-litigation "
                "settlement offer is strategically advantageous given the identified risks."
            )
        else:
            strength_narrative = (
                "The case as currently constituted carries significant legal risk. One or more fatal defects have "
                "been identified that may result in acquittal or early dismissal. Immediate remedial action is "
                "required before any litigation is initiated."
            )
            recommendation = (
                "RECOMMENDATION: Do NOT file complaint until critical defects are resolved. Consult with senior "
                "counsel regarding notice compliance, evidence gaps, and limitation deadlines. Consider whether "
                "civil recovery proceedings offer a more viable alternative."
            )

        risk_section = ""
        detected_risks = [c for c in concepts if c.get("concept") in RISK_LABELS]
        if detected_risks:
            risk_section = "\n\nIDENTIFIED RISK FACTORS:\n"
            for c in detected_risks:
                concept = c.get("concept", "")
                conf = c.get("confidence", 0)
                label = RISK_LABELS.get(concept, "")
                ref = SECTION_REFS.get(concept, "")
                risk_section += f"  [{concept.replace('_', ' ').upper()}] (Confidence: {conf:.0%})\n"
                risk_section += f"  Risk Level: {label}\n"
                risk_section += f"  Legal Reference: {ref}\n\n"

        strength_section = "\nSTRENGTHS IDENTIFIED:\n"
        positives = [c for c in concepts if c.get("concept") in ("cheque_bounce", "legal_notice_compliance", "legally_enforceable_debt", "strong_documentary_evidence")]
        if positives:
            for c in positives:
                concept = c.get("concept", "")
                ref = SECTION_REFS.get(concept, "")
                strength_section += f"  [{concept.replace('_', ' ').upper()}] — {ref}\n"
        else:
            strength_section += "  No high-confidence positive markers detected from free-text analysis.\n"

        draft = f"""
LEGAL OPINION — SECTION 138 NI ACT CASE ANALYSIS
==================================================
SUBJECT: Preliminary Case Strength Assessment
CASE STRENGTH SCORE: {score}/100
OVERALL VERDICT: {verdict.upper()}

EXECUTIVE ASSESSMENT:
{strength_narrative}

{strength_section}{risk_section}
PROCEDURAL CHECKLIST:
  [ ] Original cheque (not photocopy) secured
  [ ] Bank dishonour memo / return slip obtained
  [ ] Legal demand notice served within 30 days of dishonour
  [ ] Postal proof of notice delivery (AD card / courier receipt) available
  [ ] 15-day reply period elapsed without payment
  [ ] Complaint filed within 1 month of cause of action arising
  [ ] Certified copies of all documents ready for court submission

{recommendation}

DISCLAIMER: This is a preliminary AI-generated assessment based on structured inputs and semantic analysis.
It is not a substitute for professional legal advice. Consult a qualified advocate before proceeding.
"""
        return draft.strip()
