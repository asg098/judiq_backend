import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# ── Risk catalogue ─────────────────────────────────────────────────────────────
RISK_CATALOGUE = [
    {
        "concept_trigger": "security_cheque",
        "risk": "Security Cheque Defense (S.138)",
        "severity": "CRITICAL",
        "description": "Accused alleges the instrument was handed over as security for an unliquidated future liability, not for a present debt.",
        "rebuttal": "Counter via S.139 presumption. Per 'Sampelly Satyanarayana Rao v. Indian Renewable Energy Development Agency Ltd (2016) 10 SCC 458', a post-dated cheque for a loan installment is a valid S.138 instrument. Burden is on accused to show no debt existed on date of presentation.",
        "case_law": "Sampelly Satyanarayana Rao (2016)"
    },
    {
        "concept_trigger": "stop_payment",
        "risk": "Stop Payment Instruction Strategy",
        "severity": "HIGH",
        "description": "Accused claims they instructed the bank to 'Stop Payment' for valid reasons (e.g., breach of contract), seeking to bypass S.138.",
        "rebuttal": "Per 'Laxmi Dyechem v. State of Gujarat (2012) 13 SCC 375', Section 138 is attracted even for 'Stop Payment' if there are insufficient funds or if no valid justification is proven. Burden remains on accused to prove debt was not due.",
        "case_law": "Laxmi Dyechem (2012)"
    },
    {
        "concept_trigger": "account_closed",
        "risk": "Account Closed Tactic",
        "severity": "CRITICAL",
        "description": "The cheque was returned because the account was closed prior to presentation.",
        "rebuttal": "Per 'NEPC Micon Ltd. v. Magma Leasing Ltd. (1999) 4 SCC 253', closing an account is equivalent to 'insufficient funds' if the debt was pending. S.138 applies fully.",
        "case_law": "NEPC Micon Ltd. (1999)"
    },
    {
        "concept_trigger": "notice_defect",
        "pillar_trigger": "notice_sent",
        "risk": "Statutory Notice Lapse (S.138b)",
        "severity": "FATAL",
        "description": "Notice must be sent within 30 days of memo receipt. Failure is a non-curable jurisdictional defect.",
        "rebuttal": "If within time: Dispatch immediately. If time has elapsed: Criminal prosecution is barred; evaluate Civil Suit for Recovery (Order 37 CPC) which has a 3-year limitation.",
        "case_law": "Central Bank of India v. Saxons Farms (1999)"
    },
    {
        "concept_trigger": "material_alteration",
        "risk": "Material Alteration Defense",
        "severity": "HIGH",
        "description": "Accused claims the cheque was altered (date, amount, or name) without consent, rendering it void under S.87 of Negotiable Instruments Act.",
        "rebuttal": "Cross-examine on whether the 'alteration' was in fact a correction made by the drawer or authorized by them. Use handwriting expert (S.45 Evidence Act).",
        "case_law": "Loonkaran Sethia v. Ivan E. John (1977)"
    },
    {
        "concept_trigger": "directors_named",
        "pillar_trigger": "directors_named",
        "risk": "Vicarious Liability Defect (S.141)",
        "severity": "CRITICAL",
        "description": "For corporate accused, failure to specifically name and aver the role of directors is fatal per Aneeta Hada (2012).",
        "rebuttal": "Ensure the complaint contains specific averments that the named directors were 'in charge of and responsible for the conduct of business'. Company must be co-accused.",
        "case_law": "Aneeta Hada v. Godfather Travels (2012)"
    },
    {
        "concept_trigger": "digital_evidence",
        "risk": "Electronic Evidence Admissibility (S.65B)",
        "severity": "HIGH",
        "description": "WhatsApp/Email records are inadmissible without a mandatory certificate under Section 65B(4) of the Indian Evidence Act.",
        "rebuttal": "Per 'Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal (2020)', the certificate is a condition precedent for admissibility. Prepare certificate signed by the person in control of the device.",
        "case_law": "Arjun Panditrao Khotkar (2020)"
    },
    {
        "concept_trigger": "interim_compensation",
        "risk": "Interim Compensation Opportunity (S.143A)",
        "severity": "MEDIUM",
        "description": "Section 143A allows the court to order the accused to pay up to 20% of the cheque amount as interim compensation.",
        "rebuttal": "Proactively file an application under S.143A at the time of framing of notice/charge. This exerts financial pressure and incentivizes settlement.",
        "case_law": "L.G.R. Enterprises v. P.V. Ramakrishna (2019)"
    },
    {
        "concept_trigger": "financial_capacity_risk",
        "risk": "Financial Capacity Rebuttal (Basalingappa Rule)",
        "severity": "HIGH",
        "description": "Accused challenges the complainant's ability/means to lend the alleged high-value cash amount.",
        "rebuttal": "Counter by showing specific source of funds (bank withdrawal receipts, sale of assets, or high ITR income). Per 'Basalingappa (2019)', if the accused creates a 'probable defense' regarding financial capacity, the burden shifts back to the complainant.",
        "case_law": "Basalingappa v. Mudibasappa (2019)"
    }
]


# Mapping from score → prediction (Cynical Advocate Tuning)
OUTCOME_MAP = [
    (88, "High Probability of Conviction",      "Exceptional documentary trail. Presumptions are nearly impossible to rebut. Subject to trial technicalities."),
    (75, "Likely Conviction (Trial Risk)",       "Strong pillars, but 'reasonable doubt' remains a tactical weapon for the defense. Successful cross-examination is vital."),
    (60, "Contested Case — 50/50 Outcome",       "Case survives prima facie, but financial capacity or notice technicalities present significant acquittal risks."),
    (45, "High Risk of Acquittal",               "Defense will likely rebut presumptions. Procedural gaps provide multiple 'escape routes' for the accused."),
    ( 0, "Non-Maintainable / Fatal Defects",     "Complaint is procedurally or substantively DOA. Expect dismissal at pre-summoning or discharge stage."),
]

TRANSLATIONS = {
    "hindi": {
        "STRONG":   "मजबूत मामला — अभियोजन संभावित (Strong Case)",
        "MODERATE": "मध्यम मामला — सुधार आवश्यक (Moderate Case)",
        "WEAK":     "कमजोर मामला — वैकल्पिक विकल्प देखें (Weak Case)"
    },
    "marathi": {
        "STRONG":   "भक्कम प्रकरण — खटला फायदेशीर (Strong Case)",
        "MODERATE": "मध्यम प्रकरण — पुरावा बळकट करा (Moderate Case)",
        "WEAK":     "कमकुवत प्रकरण — नागरी दाखल विचारात घ्या (Weak Case)"
    },
    "gujarati": {
        "STRONG":   "મજબૂત કેસ — ફોજદારી ફરિયાદ ફાઈલ કરો",
        "MODERATE": "મધ્યમ કેસ — પુરાવા મજબૂત કરો",
        "WEAK":     "નબળો કેસ — સમાધાન ધ્યાનમાં લો"
    }
}


class DecisionSupportEngine:
    """
    Decision-Support Layer:
    ─ Risk identification with AI-driven rebuttals
    ─ Outcome probability prediction
    ─ Multilingual verdict translation
    ─ Evidence gap suggestions
    """

    @staticmethod
    def identify_risks_and_rebuttals(concepts: List[Dict], case_data: Dict) -> List[Dict]:
        concept_names = {c["concept"] for c in concepts}
        risks: List[Dict] = []
        seen_risks: set = set()

        for rule in RISK_CATALOGUE:
            concept_trigger = rule.get("concept_trigger")
            pillar_trigger  = rule.get("pillar_trigger")
            risk_key        = rule["risk"]

            if risk_key in seen_risks:
                continue

            fired = False

            # Fire if the semantic engine detected the concept
            if concept_trigger and concept_trigger in concept_names:
                fired = True

            # Fire if a boolean pillar is false (for structural risks)
            if pillar_trigger and not case_data.get(pillar_trigger, True):
                # Special case: corporate vicarious liability
                if pillar_trigger == "directors_named":
                    accused_type = case_data.get("accused_type", "Individual")
                    if accused_type in ("Pvt Ltd/Ltd Company", "Company", "Partnership Firm"):
                        fired = True
                else:
                    fired = True

            if fired:
                seen_risks.add(risk_key)
                risks.append({
                    "risk":        risk_key,
                    "severity":    rule["severity"],
                    "description": rule["description"],
                    "rebuttal":    rule["rebuttal"],
                    "case_law":    rule.get("case_law", "")
                })

        # Sort: FATAL → CRITICAL → HIGH → MEDIUM
        order = {"FATAL": 0, "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
        risks.sort(key=lambda r: order.get(r["severity"], 99))

        # Hard-coded strategy triggers based on case data
        if case_data.get("communication_records"):
            risks.append({
                "risk": "Digital Proof & S.65B Compliance",
                "severity": "HIGH",
                "description": "Case relies on digital trails (WhatsApp/Email) which are subject to strict admissibility rules.",
                "rebuttal": "File a mandatory Section 65B Evidence Act Certificate alongside the complaint to ensure these records are read in evidence.",
                "case_law": "Arjun Panditrao Khotkar (2020)"
            })
        
        if case_data.get("amount", 0) >= 50000:
            risks.append({
                "risk": "Strategic Recovery: S.143A Application",
                "severity": "MEDIUM",
                "description": "High-value cheque detected. Opportunity to secure 20% of the amount during trial.",
                "rebuttal": "Include a prayer for Interim Compensation under Section 143A to secure partial recovery and pressure the accused for settlement.",
                "case_law": "S.143A NI Act (2018 Amendment)"
            })

        return risks

    @staticmethod
    def predict_outcome(final_score: float) -> Dict[str, Any]:
        for threshold, prediction, rationale in OUTCOME_MAP:
            if final_score >= threshold:
                return {
                    "prediction":  prediction,
                    "probability": f"{round(final_score, 1)}%",
                    "rationale":   rationale,
                    "score_band":  (
                        "STRONG"   if final_score >= 70 else
                        "MODERATE" if final_score >= 45 else
                        "WEAK"
                    )
                }
        return {
            "prediction": "Unable to Determine",
            "probability": "0%",
            "rationale": "Insufficient data to assess outcome.",
            "score_band": "WEAK"
        }

    @staticmethod
    def translate_verdict(verdict: str, target_lang: str = "hindi") -> str:
        lang_map = TRANSLATIONS.get(target_lang.lower(), TRANSLATIONS["hindi"])
        return lang_map.get(verdict.upper(), verdict)

    @staticmethod
    def suggest_evidence_gaps(case_data: Dict) -> List[str]:
        suggestions: List[str] = []
        if not case_data.get("debt_proven"):
            suggestions += [
                "WhatsApp/Email correspondence where accused acknowledges the debt (Requires S.65B Certificate)",
                "Bank transfer records or UPI transaction receipts for the original loan disbursement",
                "Ledger account entries / Tally printout showing receivable",
                "Promissory note or acknowledgement of debt signed by accused",
                "SMS logs discussing repayment timeline or outstanding balance",
            ]
        
        if case_data.get("communication_records"):
            suggestions += [
                "Mandatory: Prepare Section 65B Evidence Act Certificate for WhatsApp/Email printouts",
                "Ensure digital records show a clear admission of liability or acknowledgment of the specific cheque",
            ]
        if not case_data.get("notice_sent"):
            suggestions += [
                "Draft and dispatch demand notice via Registered Post AD within 30 days of dishonour memo",
                "Retain original postal receipt and AD card (green card) as proof of dispatch and delivery",
            ]
        if case_data.get("accused_type") in ("Pvt Ltd/Ltd Company", "Company", "Partnership Firm") \
                and not case_data.get("directors_named"):
            suggestions += [
                "Obtain Memorandum of Association / Partnership Deed to identify directors/partners",
                "Name all directors in charge of business in the complaint with specific averments",
            ]
        if not case_data.get("dishonour_memo"):
            suggestions += [
                "Obtain certified copy of the dishonour memo from the presenting bank immediately",
                "Ensure the memo clearly states the reason for dishonour (e.g., 'Insufficient Funds')",
            ]
        return suggestions
