"""
Credit Engine 2.0 - Phrasebanks for Template-Resistant Letters

These phrasebanks provide variation for letter generation.
The variation_seed from LetterPlan determines which phrases are selected.
"""
from typing import Dict, List


# =============================================================================
# OPENING PHRASES
# =============================================================================

OPENINGS = {
    "formal": [
        "I am writing to formally dispute the following items on my credit report.",
        "This letter serves as a formal dispute regarding inaccuracies on my credit report.",
        "Pursuant to my rights under the Fair Credit Reporting Act, I am disputing the following items.",
        "I am exercising my rights under 15 U.S.C. § 1681 to dispute inaccurate information.",
        "Please accept this letter as a formal dispute of the items listed below.",
    ],
    "assertive": [
        "I demand that you investigate and correct the following errors on my credit report.",
        "I am disputing the following items which are being reported inaccurately.",
        "The following information on my credit report is incorrect and must be corrected.",
        "I require immediate investigation of the following inaccurate items.",
        "These items are being reported in violation of federal law and must be addressed.",
    ],
    "conversational": [
        "I've reviewed my credit report and found some items that appear to be inaccurate.",
        "After checking my credit report, I noticed several errors that need to be corrected.",
        "I'm writing because I found some problems with my credit report that I'd like fixed.",
        "My credit report contains information that doesn't appear to be accurate.",
        "I need your help correcting some errors I've discovered on my credit report.",
    ],
    "narrative": [
        "I want to share my experience with what I found on my credit report.",
        "After reviewing my credit report, I need to bring some concerns to your attention.",
        "Let me explain the issues I've discovered with my credit report.",
        "I'm writing to you today about problems I found when checking my credit.",
        "When I pulled my credit report recently, I was surprised by what I found.",
    ],
}


# =============================================================================
# VIOLATION-SPECIFIC PHRASES
# =============================================================================

VIOLATION_PHRASES = {
    "missing_dofd": [
        "This account is missing the required Date of First Delinquency (DOFD) in Metro 2 Field 25.",
        "The Date of First Delinquency is not reported, making it impossible to determine the 7-year reporting period.",
        "No DOFD is shown for this derogatory account, which is a Metro 2 compliance failure.",
        "This account lacks the mandatory DOFD field required for derogatory tradelines.",
    ],
    "obsolete_account": [
        "This account has exceeded the 7-year reporting limit under FCRA §605(a).",
        "The 7-year reporting period has expired based on the Date of First Delinquency.",
        "This account is obsolete and should have been removed from my credit report.",
        "Under FCRA §605(a), this item is past its legal reporting period and must be deleted.",
    ],
    "negative_balance": [
        "This account shows a negative balance, which is invalid under Metro 2 standards.",
        "A negative balance is being reported, which is mathematically impossible.",
        "The reported negative balance indicates unverified or erroneous data.",
    ],
    "past_due_exceeds_balance": [
        "The past due amount exceeds the total balance, which is mathematically impossible.",
        "Field 17B (past due) is greater than Field 17A (balance), indicating data corruption.",
        "The past due amount cannot logically exceed the account balance.",
    ],
    "future_date": [
        "A future date is being reported, indicating unverified information.",
        "Dates in the future cannot be accurate and suggest the data was not properly verified.",
        "Future dates demonstrate that this information has not been verified for accuracy.",
    ],
    "closed_oc_reporting_balance": [
        "This closed original creditor account is incorrectly reporting a balance.",
        "A closed OC account should report $0 balance if the debt was transferred.",
        "Only the current debt holder should report a balance on this account.",
    ],
    "missing_date_opened": [
        "This account is missing the Date Opened field, a required Metro 2 data point.",
        "The account opening date is not reported, which is required for proper credit history.",
        "Without a Date Opened, the account history cannot be properly evaluated.",
    ],
    "missing_dla": [
        "This account is missing the Date Last Activity, making the data appear stale.",
        "The Date Last Activity is not reported, suggesting this account data may be outdated.",
        "Without recent activity dates, this account information cannot be verified as current.",
    ],
    "impossible_timeline": [
        "The dates on this account create an impossible timeline.",
        "The chronological sequence of dates is logically impossible.",
        "This account contains date inconsistencies that violate basic logic.",
    ],
    "stale_reporting": [
        "This account has not been updated in over 90 days and may contain outdated information.",
        "The last reported date is significantly old, suggesting the data may be stale.",
        "This account appears to have stale data that has not been recently verified.",
    ],
    "missing_original_creditor": [
        "This collection account does not identify the original creditor.",
        "The original creditor is not reported, making debt verification impossible.",
        "Without the original creditor name, I cannot verify this debt's legitimacy.",
    ],
    "chargeoff_missing_dofd": [
        "This charge-off account is missing the required DOFD for 7-year calculation.",
        "Charge-off accounts must report DOFD to comply with FCRA reporting limits.",
        "The absence of DOFD on this charge-off prevents proper obsolescence tracking.",
    ],
    "closed_oc_reporting_past_due": [
        "This closed account is incorrectly reporting a past due amount.",
        "A closed original creditor account should not report past due balances.",
        "The past due amount on this closed account is incorrect.",
    ],
    "balance_exceeds_high_credit": [
        "The current balance exceeds the high credit amount, which is inconsistent.",
        "Balance cannot logically exceed the high credit ever reached on this account.",
        "This balance-to-high-credit relationship is mathematically invalid.",
    ],
    "negative_credit_limit": [
        "A negative credit limit is being reported, which is invalid.",
        "Credit limits cannot be negative - this indicates unverified data.",
        "The negative credit limit suggests this account data was not properly validated.",
    ],
}


# =============================================================================
# CLOSING PHRASES
# =============================================================================

CLOSINGS = {
    "formal": [
        "Please investigate these items and provide me with the results within 30 days as required by law.",
        "I expect a response within the timeframe mandated by the Fair Credit Reporting Act.",
        "Please correct these errors and send me an updated copy of my credit report.",
        "Pursuant to FCRA §611(a), please complete your investigation within 30 days.",
    ],
    "assertive": [
        "I expect these items to be corrected or removed within the legally mandated timeframe.",
        "Failure to investigate and correct these errors may result in further legal action.",
        "I require confirmation that these items have been investigated and corrected.",
        "These violations must be addressed immediately to bring my credit report into compliance.",
    ],
    "conversational": [
        "Thank you for looking into this. I look forward to your response.",
        "I appreciate your help in getting these errors corrected.",
        "Please let me know if you need any additional information from me.",
        "Thanks for your attention to this matter.",
    ],
    "narrative": [
        "I hope this helps explain why I believe these items need to be corrected.",
        "I trust you'll understand my concerns and investigate accordingly.",
        "Thank you for taking the time to review my situation.",
        "I look forward to hearing back from you about what you find.",
    ],
}


# =============================================================================
# TRANSITION PHRASES
# =============================================================================

TRANSITIONS = [
    "Additionally,",
    "Furthermore,",
    "I also dispute the following:",
    "The next item I am disputing is:",
    "Another error on my report:",
    "In addition to the above,",
    "I am also disputing:",
    "Next,",
]


# =============================================================================
# FCRA REFERENCE PHRASES
# =============================================================================

FCRA_REFERENCES = {
    "605(a)": [
        "Under FCRA §605(a), credit bureaus may not report accounts more than 7 years from the DOFD.",
        "FCRA §605(a)(4) prohibits reporting of accounts placed for collection beyond 7 years.",
        "The Fair Credit Reporting Act, Section 605(a), limits the reporting period for negative items.",
    ],
    "605(c)(1)": [
        "FCRA §605(c)(1) requires the 7-year period to run from the Date of First Delinquency.",
        "Under §605(c)(1), the DOFD is the required starting point for the reporting period.",
        "The Fair Credit Reporting Act mandates that DOFD be used to calculate the 7-year limit.",
    ],
    "611(a)": [
        "Under FCRA §611(a), furnishers must report complete and accurate information.",
        "FCRA §611(a) requires credit bureaus to ensure the accuracy of reported information.",
        "Section 611(a) of the FCRA establishes accuracy requirements for credit reporting.",
    ],
}


# =============================================================================
# COMBINED PHRASEBANKS DICTIONARY
# =============================================================================

PHRASEBANKS = {
    "openings": OPENINGS,
    "violations": VIOLATION_PHRASES,
    "closings": CLOSINGS,
    "transitions": TRANSITIONS,
    "fcra_references": FCRA_REFERENCES,
}
