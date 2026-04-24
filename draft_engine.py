def generate_complaint(case_data: Dict, concepts: List[Dict]) -> str:
    """Generate criminal complaint with ALL fields auto-filled"""
    today, amount_str = _case_meta(case_data)
    
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
