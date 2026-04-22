import logging
from datetime import datetime, date
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def decide_draft_type(score: int, concepts: List[Dict], case_data: Dict) -> str:
    concept_names = {c.get("concept", "") for c in concepts}
    if not case_data.get("notice_sent"):
        return "LEGAL_NOTICE"
    if "limitation_issue" in concept_names:
        return "DELAY_CONDONATION"
    if score > 75:
        return "COMPLAINT"
    if score < 40:
        if concept_names & {"security_cheque", "cheque_misuse", "signature_dispute", "no_agreement"}:
            return "DEFENCE_STRATEGY"
        return "DEFENCE_REPLY"
    if 40 <= score <= 70:
        return "SETTLEMENT"
    return "LEGAL_OPINION"


def _header(title: str) -> str:
    line = "=" * 70
    return f"{line}\n{title}\n{line}"


def _case_meta(case_data: Dict) -> str:
    today = datetime.now().strftime("%d %B %Y")
    amount = case_data.get("amount", "[AMOUNT]")
    if isinstance(amount, (int, float)) and amount > 0:
        if amount >= 100000:
            amount_str = f"Rs. {amount:,.0f}/- (Rupees {_num_to_words(int(amount))} only)"
        else:
            amount_str = f"Rs. {amount:,.0f}/-"
    else:
        amount_str = "Rs. ___________/-"
    return today, amount_str


def _num_to_words(n: int) -> str:
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    if n == 0: return "Zero"
    if n < 20: return ones[n]
    if n < 100: return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
    if n < 1000: return ones[n // 100] + " Hundred" + (" and " + _num_to_words(n % 100) if n % 100 else "")
    if n < 100000: return _num_to_words(n // 1000) + " Thousand" + (" " + _num_to_words(n % 1000) if n % 1000 else "")
    if n < 10000000: return _num_to_words(n // 100000) + " Lakh" + (" " + _num_to_words(n % 100000) if n % 100000 else "")
    return _num_to_words(n // 10000000) + " Crore" + (" " + _num_to_words(n % 10000000) if n % 10000000 else "")


def generate_legal_notice(case_data: Dict) -> str:
    """Generate legal notice with ALL fields auto-filled from case data"""
    today, amount_str = _case_meta(case_data)
    
    # Extract all fields with proper fallbacks
    complainant = case_data.get("complainant_name") or case_data.get("complainantName") or "[YOUR NAME]"
    accused = case_data.get("accused_name") or case_data.get("accusedName") or "[ACCUSED NAME]"
    accused_addr = case_data.get("accused_address") or case_data.get("accusedAddress") or "[ACCUSED ADDRESS]"
    
    cheque_no = case_data.get("cheque_number") or case_data.get("chequeNumber") or "______"
    cheque_date = case_data.get("cheque_date") or case_data.get("chequeDate") or "[DATE]"
    bank = case_data.get("bank_name") or case_data.get("bankName") or "[BANK NAME]"
    branch = case_data.get("branch_name") or case_data.get("branchName") or ""
    bank_full = f"{bank}, {branch}" if branch else bank
    
    dishonour_date = case_data.get("dishonour_date") or case_data.get("dishonourDate") or "[DATE]"
    dishonour_reason = case_data.get("dishonour_reason") or case_data.get("dishonourReason") or "Funds Insufficient"
    
    # Extract transaction nature from description or field
    description = case_data.get("description", "")
    purpose = case_data.get("purpose", "")
    
    # Determine nature of transaction
    transaction_nature = "a legally enforceable debt/liability"
    if "loan" in description.lower() or "loan" in purpose.lower():
        transaction_nature = "a loan advanced"
    elif "goods" in description.lower() or "supply" in purpose.lower():
        transaction_nature = "goods supplied"
    elif "service" in description.lower():
        transaction_nature = "services rendered"
    elif purpose:
        transaction_nature = purpose[:100]  # Use first 100 chars of purpose
    
    return f"""{_header("LEGAL NOTICE UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881")}

Date: {today}

To,
{accused}
{accused_addr}

THROUGH REGISTERED POST (AD)

Sub: LEGAL NOTICE FOR DISHONOUR OF CHEQUE — DEMAND FOR PAYMENT OF {amount_str}

Sir/Madam,

Under instructions from and on behalf of my client {complainant}, I hereby serve upon you the following legal notice:

1. BACKGROUND OF TRANSACTION:
   My client states that you are indebted to my client for a sum of {amount_str} in respect of {transaction_nature} made between you and my client.

2. THE CHEQUE:
   In discharge of the aforesaid legally enforceable liability, you issued a cheque bearing No. {cheque_no}, dated {cheque_date}, drawn on {bank_full}, in favour of my client for {amount_str}.

3. DISHONOUR OF CHEQUE:
   When my client presented the said cheque for encashment through banking channels, the same was returned/dishonoured on {dishonour_date} with the bank memo citing the reason "{dishonour_reason}".

4. DEMAND FOR PAYMENT:
   By this notice, my client hereby demands that you pay the said sum of {amount_str} together with interest thereon within FIFTEEN (15) DAYS from the date of receipt of this notice.

5. LEGAL CONSEQUENCE:
   You are hereby warned that in the event of your failure to make payment within the stipulated period, my client shall be constrained to initiate criminal proceedings against you under Section 138 of the Negotiable Instruments Act, 1881, and also civil proceedings for recovery of the said amount together with interest, costs, and damages, without any further notice to you.

Yours faithfully,

[ADVOCATE NAME]
Advocate & Legal Advisor
[BAR REGISTRATION NUMBER]
[CONTACT / CHAMBER ADDRESS]

On behalf of: {complainant}
"""


def generate_complaint(case_data: Dict, concepts: List[Dict]) -> str:
    """Generate criminal complaint with ALL fields auto-filled"""
    today, amount_str = _case_meta(case_data)
    
    # Extract all fields with proper fallbacks
    complainant = case_data.get("complainant_name") or case_data.get("complainantName") or "[COMPLAINANT NAME]"
    complainant_addr = case_data.get("complainant_address") or case_data.get("complainantAddress") or "[COMPLAINANT ADDRESS]"
    complainant_phone = case_data.get("complainant_phone") or case_data.get("complainantPhone") or "[CONTACT]"
    
    accused = case_data.get("accused_name") or case_data.get("accusedName") or "[ACCUSED NAME]"
    accused_addr = case_data.get("accused_address") or case_data.get("accusedAddress") or "[ACCUSED ADDRESS]"
    
    cheque_no = case_data.get("cheque_number") or case_data.get("chequeNumber") or "______"
    cheque_date = case_data.get("cheque_date") or case_data.get("chequeDate") or "[DATE]"
    bank = case_data.get("bank_name") or case_data.get("bankName") or "[BANK NAME]"
    branch = case_data.get("branch_name") or case_data.get("branchName") or ""
    bank_full = f"{bank}, {branch}" if branch else bank
    
    dishonour_date = case_data.get("dishonour_date") or case_data.get("dishonourDate") or "[DATE]"
    dishonour_reason = case_data.get("dishonour_reason") or case_data.get("dishonourReason") or "Insufficient Funds"
    notice_date = case_data.get("notice_date") or case_data.get("noticeDate") or "[NOTICE DATE]"
    
    court_name = case_data.get("court_name") or case_data.get("courtName") or "District Court"
    
    # Determine nature of transaction
    description = case_data.get("description", "")
    purpose = case_data.get("purpose", "")
    
    transaction_nature = "a legally enforceable debt"
    occupation = "business/profession"
    
    if "loan" in description.lower() or "loan" in purpose.lower():
        transaction_nature = "a loan transaction"
        occupation = "lending/financing business"
    elif "goods" in description.lower() or "supply" in purpose.lower():
        transaction_nature = "supply of goods"
        occupation = "trade and commerce"
    elif "service" in description.lower():
        transaction_nature = "provision of services"
        occupation = "service provider"
    elif purpose:
        transaction_nature = purpose[:100]

    return f"""{_header("CRIMINAL COMPLAINT UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881")}

IN THE COURT OF THE LEARNED JUDICIAL MAGISTRATE FIRST CLASS / METROPOLITAN MAGISTRATE
AT {court_name}

COMPLAINT NO.: _____ / {datetime.now().year}

IN THE MATTER OF:

COMPLAINANT:    {complainant}
                {complainant_addr}
                {complainant_phone}

VERSUS

ACCUSED:        {accused}
                {accused_addr}

COMPLAINT U/S 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881

RESPECTFULLY SHOWETH:

1. THE COMPLAINANT:
   The Complainant, {complainant}, is a law-abiding citizen/entity carrying on {occupation} and is competent to file this complaint.

2. THE ACCUSED:
   The Accused, {accused}, residing at {accused_addr}, is known to the Complainant and has been engaged in transactions with the Complainant.

3. THE LEGALLY ENFORCEABLE DEBT:
   The Complainant states that the Accused is indebted to the Complainant for a sum of {amount_str} arising from {transaction_nature}. The said debt is legally enforceable and constitutes a valid liability under law.

4. ISSUANCE OF CHEQUE:
   In discharge of the aforesaid legal liability, the Accused issued a cheque bearing No. {cheque_no}, dated {cheque_date}, drawn on {bank_full}, for an amount of {amount_str} in favour of the Complainant.

5. PRESENTATION AND DISHONOUR:
   The Complainant duly presented the said cheque for encashment. However, the said cheque was returned/dishonoured on {dishonour_date} with the bank memo citing "{dishonour_reason}", thereby constituting an offence under Section 138 of the NI Act, 1881.

6. STATUTORY DEMAND NOTICE:
   As mandated under Section 138(b) of the NI Act, the Complainant caused a legal notice to be served upon the Accused on {notice_date} through Registered Post (AD), demanding payment of {amount_str} within 15 days of receipt of the notice.

7. FAILURE TO PAY:
   Despite receipt of the aforesaid notice, the Accused has wilfully and deliberately failed, neglected, and refused to make payment of the said amount, thereby committing an offence punishable under Section 138 of the Negotiable Instruments Act, 1881.

8. CAUSE OF ACTION:
   The cause of action for this Complaint arose on the date of dishonour ({dishonour_date}) and further on expiry of the 15-day notice period. This Complaint is being filed within the limitation period prescribed under Section 142 of the NI Act, 1881.

9. JURISDICTION:
   This Hon'ble Court has jurisdiction to try this Complaint as the cheque was drawn/presented/dishonoured and/or the notice was dispatched from within the territorial jurisdiction of this Court.

10. PRAYER:
    It is, therefore, most respectfully prayed that this Hon'ble Court may be pleased to:
    
    a) Take cognizance of the offence under Section 138 of the Negotiable Instruments Act, 1881 committed by the Accused;
    
    b) Summon the Accused to face trial;
    
    c) After due trial, convict and sentence the Accused as per law;
    
    d) Direct the Accused to pay compensation of {amount_str} to the Complainant under Section 357 Cr.P.C. read with Section 138 of the NI Act;
    
    e) Pass such other and further orders as this Hon'ble Court may deem fit and proper in the interest of justice.

Date: {today}
Place: {court_name}

                                                    {complainant}
                                                    (Complainant)

VERIFICATION:
I, {complainant}, the Complainant above-named, do hereby verify that the contents of paras 1 to 10 of the above complaint are true and correct to my knowledge and belief, and nothing material has been concealed therefrom.

Verified at {court_name} on this day {today}.

                                                    {complainant}
                                                    (Complainant)

ADVOCATE ON RECORD:
[ADVOCATE NAME]
[BAR REGISTRATION NUMBER]
"""

7. FAILURE TO PAY:
   Despite receipt of the aforesaid notice, the Accused has wilfully and deliberately failed, neglected, and refused to make payment of the said amount, thereby committing an offence punishable under Section 138 of the Negotiable Instruments Act, 1881.

8. CAUSE OF ACTION:
   The cause of action for this Complaint arose on the date of dishonour ({dishonour_date}) and further on expiry of the 15-day notice period. This Complaint is being filed within the limitation period prescribed under Section 142 of the NI Act, 1881.

9. JURISDICTION:
   This Hon'ble Court has jurisdiction to try this Complaint as the cheque was drawn/presented/dishonoured and/or the notice was dispatched from within the territorial jurisdiction of this Court.

10. PRAYER:
    It is, therefore, most respectfully prayed that this Hon'ble Court may be pleased to:
    (a) Take cognizance of the offence committed by the Accused under Section 138 of the NI Act, 1881;
    (b) Issue summons to the Accused and try the Accused for the said offence;
    (c) On conviction, sentence the Accused to imprisonment as prescribed under Section 138 of the NI Act, 1881, and/or impose a fine of twice the cheque amount; and
    (d) Pass such other order(s) as this Hon'ble Court may deem fit and proper in the interest of justice.

VERIFICATION:
I, {complainant}, do hereby solemnly verify that the contents of the above Complaint are true and correct to the best of my knowledge, information, and belief. Nothing material has been concealed.

Place: [PLACE]
Date: {today}

                                                        {complainant}
                                                        (Complainant)

Drafted and filed by:
[ADVOCATE NAME]
[BAR REGISTRATION NUMBER]
"""


def generate_defence_strategy(case_data: Dict, concepts: List[Dict], score: int) -> str:
    today, amount_str = _case_meta(case_data)
    concept_names = {c.get("concept", "") for c in concepts}

    defences_identified = []
    legal_arguments = []

    if "security_cheque" in concept_names:
        defences_identified.append("Cheque Given as Security — Not for Debt Discharge")
        legal_arguments.append(
            "The cheque in question was given purely as a security/collateral cheque and not in discharge of any legally enforceable debt. As per the Hon'ble Supreme Court in Indus Airways Pvt. Ltd. v. Magnum Aviation Pvt. Ltd. (2014), a security cheque falls outside the scope of Section 138 NI Act, as there is no legally enforceable debt against which the cheque was drawn."
        )
    if "signature_dispute" in concept_names:
        defences_identified.append("Signature on Cheque Not Genuine — Forgery Alleged")
        legal_arguments.append(
            "The Accused specifically denies that the signature on the dishonoured cheque is his/her genuine signature. It is submitted that the signature has been forged/fabricated. The Complainant bears the burden of proving the signature's authenticity. A handwriting expert's examination is essential. Refer: Modi Cements Ltd. v. Kuchil Kumar Nandi (2013) — mere presumption cannot override a bona fide denial of signature."
        )
    if "no_agreement" in concept_names:
        defences_identified.append("Absence of Written Agreement — Debt Not Established")
        legal_arguments.append(
            "There is no written agreement, contract of loan, or documentary evidence establishing the alleged debt. Without a legally documented basis, the Complainant cannot invoke the presumption under Section 139 NI Act. Kumar Exports v. Sharma Carpets (2009) — the presumption under S.139 can be rebutted by showing absence of consideration."
        )
    if "no_debt_proof" in concept_names:
        defences_identified.append("No Legally Enforceable Debt or Liability Exists")
        legal_arguments.append(
            "The Accused denies existence of any legally enforceable debt or liability. The Complainant has failed to produce any loan agreement, bank transfer records, invoice, or corroborating evidence. Section 138 NI Act requires the cheque to be drawn 'in discharge of any debt or other liability' — absence of underlying debt is a complete defence."
        )
    if "cheque_misuse" in concept_names:
        defences_identified.append("Cheque Was Misused / Misappropriated")
        legal_arguments.append(
            "The cheque was issued for a specific, limited purpose and has been misused/misappropriated by the Complainant. The Accused submits that the cheque was not issued in discharge of the liability alleged. The Complainant's act of presenting the cheque for encashment beyond its intended purpose constitutes dishonest misuse."
        )

    defences_text = "\n".join([f"   {i+1}. {d}" for i, d in enumerate(defences_identified)]) if defences_identified else "   (To be determined based on full case facts)"
    arguments_text = "\n\n".join([f"   {i+1}. {a}" for i, a in enumerate(legal_arguments)]) if legal_arguments else "   (Legal arguments to be elaborated based on specific case documents)"

    return f"""{_header("DEFENCE STRATEGY BRIEF — SECTION 138 NI ACT")}

Date: {today}
Case Strength Score: {score}/100
Classification: DEFENCE-SIDED (ACCUSED STRATEGY)

DEFENCES IDENTIFIED:
{defences_text}

DETAILED LEGAL ARGUMENTS:

{arguments_text}

EVIDENTIARY STRATEGY:
   1. Dispute the genuineness and purpose of the cheque through sworn affidavit.
   2. File application under Section 91 CrPC to call for original transaction documents.
   3. Commission handwriting expert if signature is disputed.
   4. Cross-examine Complainant on the nature, purpose, and quantum of alleged debt.
   5. Produce all communications (WhatsApp, email, letters) showing the true purpose of the cheque.

PROCEDURAL STEPS:
   1. Appear before Court on date of first hearing; do NOT ignore summons.
   2. File detailed reply to complaint on first or second date.
   3. Apply for bail (if required) and obtain anticipatory bail preemptively.
   4. File application under Section 145(2) NI Act to cross-examine the Complainant.
   5. Consider filing complaint under Section 500 IPC (defamation) if allegations are false.

SETTLEMENT ASSESSMENT:
   Given the case strength score of {score}/100, a negotiated settlement may be advisable to avoid
   prolonged litigation risk. The Accused should evaluate a commercial resolution.

DISCLAIMER: This is an AI-generated preliminary strategy document. Consult a qualified advocate
before taking any legal action.
"""


def generate_settlement_draft(case_data: Dict, score: int) -> str:
    today, amount_str = _case_meta(case_data)
    complainant = case_data.get("complainant_name", "[COMPLAINANT NAME]")
    accused = case_data.get("accused_name", "[ACCUSED NAME]")

    return f"""{_header("SETTLEMENT / COMPOUNDING PROPOSAL — SECTION 138 NI ACT")}

Date: {today}
Case Strength Score: {score}/100

WITHOUT PREJUDICE

To,
{accused} / Counsel for the Accused

Re: Proposal for Compounding of Offence under Section 138 / 147 NI Act

Dear Sir/Madam,

We write on behalf of our client {complainant} in the matter of the dishonoured cheque for {amount_str}.

Pursuant to Section 147 of the Negotiable Instruments Act, 1881, the offence under Section 138 is compoundable. Our client, whilst maintaining that the complaint is fully justified and legally tenable, is open to exploring an amicable resolution to avoid protracted litigation.

TERMS PROPOSED FOR SETTLEMENT:

1. PRINCIPAL AMOUNT: Full payment of cheque amount {amount_str}.
2. INTEREST: Interest @ 18% per annum from the date of dishonour to date of settlement.
3. LEGAL COSTS: Contribution towards legal costs incurred (to be agreed).
4. TIMELINE: Full payment within ___ days of signing of settlement agreement.
5. WITHDRAWAL: Upon receipt of agreed settlement amount, the Complainant agrees to file a joint application for compounding before the Hon'ble Court under Section 147 NI Act.

This proposal is made without prejudice to the legal rights of our client and shall not be construed as an admission of any weakness in the case.

Kindly revert with your response within 7 working days.

Yours faithfully,

[ADVOCATE NAME]
For and on behalf of {complainant}

Note: Case Strength Score {score}/100 — Moderate case; early settlement is strategically recommended.
"""


def generate_delay_condonation(case_data: Dict) -> str:
    today, amount_str = _case_meta(case_data)
    complainant = case_data.get("complainant_name", "[COMPLAINANT NAME]")

    return f"""{_header("APPLICATION FOR CONDONATION OF DELAY — SECTION 142 NI ACT r/w SECTION 5 LIMITATION ACT")}

IN THE COURT OF THE LEARNED JUDICIAL MAGISTRATE / METROPOLITAN MAGISTRATE
AT [COURT LOCATION]

COMPLAINT NO.: _____ / {datetime.now().year}

IN THE MATTER OF:
{complainant}                                              ... COMPLAINANT
VERSUS
[ACCUSED NAME]                                             ... ACCUSED

APPLICATION FOR CONDONATION OF DELAY IN FILING COMPLAINT U/S 138 NI ACT

RESPECTFULLY SHOWETH:

1. The Complainant has filed a Complaint under Section 138 of the Negotiable Instruments Act, 1881.

2. The cheque was dishonoured on [DISHONOUR DATE] and the statutory demand notice was served on [NOTICE DATE]. The 15-day period expired on [EXPIRY DATE].

3. The Complaint ought to have been filed by [LIMITATION DATE]. However, the Complaint has been filed on {today}, resulting in a delay of approximately ___ days.

4. REASONS FOR DELAY (SUFFICIENT CAUSE):
   [Describe genuine reasons — illness, unavailability of advocate, miscommunication, etc.]

5. The Complainant submits that the delay was not intentional or deliberate and occurred due to circumstances beyond the Complainant's control.

6. The Complainant relies upon the settled principle that courts should adopt a liberal approach in condonation matters where sufficient cause is shown, and that technical delay should not defeat substantive justice. (Saketh India Ltd. v. India Securities Ltd., 1999)

7. No prejudice will be caused to the Accused by condoning the said delay.

PRAYER:
It is prayed that this Hon'ble Court may be pleased to condone the delay of ___ days in filing this Complaint and admit the Complaint for hearing.

Place: [PLACE]
Date: {today}

                                                        {complainant}
                                                        (Complainant)
Advocate: [ADVOCATE NAME]
"""


def generate_legal_opinion(score: int, concepts: List[Dict], case_data: Dict) -> str:
    today, amount_str = _case_meta(case_data)
    concept_names = {c.get("concept", "") for c in concepts}

    if score >= 75:
        strength_narrative = "The case presents a strong evidentiary foundation. All primary conditions under Section 138 NI Act appear satisfied. The Complainant is well-positioned to proceed with prosecution."
        recommendation = "PROCEED: File complaint before the jurisdictional Magistrate. Ensure all original documents are secured."
    elif score >= 50:
        strength_narrative = "The case has moderate legal strength but exhibits identifiable risk factors. Pre-litigation preparation is essential before filing."
        recommendation = "PREPARE: Address identified weaknesses. Obtain additional corroborating evidence before filing."
    else:
        strength_narrative = "The case carries significant legal risk. One or more fatal defects have been identified that may result in acquittal or dismissal."
        recommendation = "CAUTION: Do NOT file until critical defects are resolved. Evaluate civil recovery as an alternative."

    risk_items = []
    for c in concepts:
        if c.get("concept") in {"notice_defect", "no_debt_proof", "security_cheque", "signature_dispute", "limitation_issue", "cheque_misuse", "no_agreement"}:
            risk_items.append(f"   → {c['concept'].replace('_',' ').upper()} (confidence: {c['confidence']:.0%})")

    risk_text = "\n".join(risk_items) if risk_items else "   → No significant risk factors detected."

    checklist = []
    if case_data.get("cheque_present"): checklist.append("   [✓] Original cheque secured")
    else: checklist.append("   [✗] Original cheque MISSING — critical")
    if case_data.get("dishonour_memo"): checklist.append("   [✓] Bank dishonour memo available")
    else: checklist.append("   [✗] Bank dishonour memo MISSING")
    if case_data.get("notice_sent"): checklist.append("   [✓] Statutory demand notice served")
    else: checklist.append("   [✗] Statutory demand notice NOT SENT — fatal defect")
    if case_data.get("debt_proven"): checklist.append("   [✓] Debt/liability established")
    else: checklist.append("   [✗] Underlying debt proof MISSING")

    checklist_text = "\n".join(checklist)

    return f"""{_header("LEGAL OPINION — SECTION 138 NI ACT CASE ANALYSIS")}

Date: {today}
Case Strength Score: {score}/100
Amount in Dispute: {amount_str}

EXECUTIVE ASSESSMENT:
{strength_narrative}

RISK FACTORS IDENTIFIED:
{risk_text}

DOCUMENT CHECKLIST:
{checklist_text}

RECOMMENDATION:
{recommendation}

PROCEDURAL CHECKLIST:
   [ ] Confirm cheque was presented within 3 months of its date
   [ ] Confirm demand notice dispatched within 30 days of dishonour
   [ ] Confirm 15-day notice response period has elapsed
   [ ] Confirm complaint filed within 1 month of cause of action
   [ ] Certified copies of all documents ready for court submission

DISCLAIMER: AI-generated preliminary assessment. Not a substitute for professional legal advice.
"""


class DraftEngine:
    @staticmethod
    def generate_opinion(analysis_result: Dict[str, Any]) -> str:
        score = analysis_result.get("score", 0)
        concepts = analysis_result.get("concepts", [])
        case_data = analysis_result.get("case_data", {})

        draft_type = decide_draft_type(score, concepts, case_data)
        return DraftEngine.generate_draft(draft_type, score, concepts, case_data)

    @staticmethod
    def generate_draft(draft_type: str, score: int, concepts: List[Dict], case_data: Dict) -> str:
        if draft_type == "LEGAL_NOTICE":
            return generate_legal_notice(case_data)
        elif draft_type == "COMPLAINT":
            return generate_complaint(case_data, concepts)
        elif draft_type == "DEFENCE_STRATEGY":
            return generate_defence_strategy(case_data, concepts, score)
        elif draft_type == "DEFENCE_REPLY":
            return generate_defence_strategy(case_data, concepts, score)
        elif draft_type == "SETTLEMENT":
            return generate_settlement_draft(case_data, score)
        elif draft_type == "DELAY_CONDONATION":
            return generate_delay_condonation(case_data)
        else:
            return generate_legal_opinion(score, concepts, case_data)
