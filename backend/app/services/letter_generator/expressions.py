"""
Credit Copilot - Violation Expressions Database

Human-language expressions for each violation type.
Each violation has 8-10 natural language variations that sound like
a real consumer wrote them, not a template.

Key principles:
- Mix sentence lengths (short and conversational)
- Vary how the issue is referenced
- Some include context, others are direct
- Avoid using exact same words/structure
- Sound like a consumer, not a lawyer
"""
from typing import Dict, List


# =============================================================================
# VIOLATION EXPRESSIONS - 8-10 variations per type
# =============================================================================

VIOLATION_EXPRESSIONS: Dict[str, List[str]] = {
    # Missing Date of First Delinquency
    "missing_dofd": [
        "I noticed the date of first delinquency isn't shown for this account",
        "There's no Date of First Delinquency reported here, which seems incomplete",
        "The DOFD field appears to be missing from this tradeline",
        "When I reviewed this account, I couldn't find any date of first delinquency listed",
        "This account doesn't show when the delinquency supposedly started",
        "The required DOFD information isn't appearing on this account",
        "I see this account is missing the date indicating when problems began",
        "Looking at this tradeline, the first delinquency date isn't reported",
        "This negative account shows no DOFD, making it impossible to verify the reporting period",
        "Without a date of first delinquency showing, how can the 7-year limit be calculated?",
    ],

    # Stale/Outdated Data
    "stale_reporting": [
        "This account hasn't been updated in quite a while and the data seems outdated",
        "The last update on this account was a long time ago, which concerns me",
        "It looks like this information is stale and hasn't been verified recently",
        "This tradeline appears to have old data that may no longer be accurate",
        "When was this account last verified? The reporting date is very old",
        "This account seems to contain outdated information that needs to be refreshed",
        "The data on this account appears stale and potentially unreliable",
        "I'm concerned this account information is too old to be accurate",
        "This tradeline hasn't been updated recently and may contain errors",
        "The reporting on this account looks outdated and should be verified",
    ],

    # Missing Scheduled Payment
    "missing_scheduled_payment": [
        "I noticed the monthly payment amount isn't shown on this account",
        "The payment information appears incomplete - there's no scheduled payment listed",
        "When reviewing this account, I saw the payment amount is missing",
        "This account doesn't show what my monthly payment should be",
        "The scheduled payment field seems to be blank for this tradeline",
        "I couldn't find any payment amount information on this account",
        "This account is missing the required payment amount details",
        "No monthly payment is showing for this account, which seems wrong",
        "The payment amount isn't being reported for this tradeline",
        "Looking at this account, I don't see any scheduled payment information",
    ],

    # Obsolete Account (beyond 7-year limit)
    "obsolete_account": [
        "This account appears to be past the 7-year reporting limit",
        "Based on my calculations, this item should have aged off my report by now",
        "This account seems too old to still be appearing on my credit report",
        "The 7-year period for this item has passed - why is it still showing?",
        "This tradeline appears obsolete and should no longer be reported",
        "I believe this account has exceeded its legal reporting period",
        "This item looks like it should have dropped off by now based on its age",
        "According to the dates, this account is past the time it can be reported",
        "This old account shouldn't still be appearing on my report",
        "Based on the DOFD, this item's reporting period should have ended",
    ],

    # Negative Balance
    "negative_balance": [
        "This account is showing a negative balance, which doesn't make sense",
        "I noticed a negative balance being reported, which seems impossible",
        "How can an account have a negative balance? This appears to be an error",
        "The balance shown is negative, which I don't understand",
        "A negative balance is being reported on this account - that can't be right",
        "This tradeline shows a balance below zero, which isn't possible",
        "The negative balance on this account indicates something is wrong",
        "I see a minus sign on the balance, which doesn't seem accurate",
    ],

    # Past Due Exceeds Balance
    "past_due_exceeds_balance": [
        "The past due amount is more than the total balance, which is impossible",
        "How can I owe more past due than the entire balance? Something's wrong here",
        "The past due shown exceeds the balance - that doesn't add up",
        "This account shows past due greater than balance, which can't be right",
        "The numbers don't make sense - past due is higher than total owed",
        "I noticed the past due amount is larger than my balance, which is incorrect",
        "Something is off - the past due exceeds what's supposedly owed",
        "The past due and balance figures don't make mathematical sense",
    ],

    # Future Date
    "future_date": [
        "There's a date on this account that's in the future, which is impossible",
        "I noticed a future date being reported, which can't be accurate",
        "How can there be a date that hasn't happened yet on my credit report?",
        "This account shows a date that's in the future - that's clearly an error",
        "A date from the future is appearing on this tradeline",
        "The dates on this account include one that hasn't occurred yet",
        "I see a future date on this account, which obviously isn't right",
        "This item has impossible future dates that need correction",
    ],

    # Missing Date Opened
    "missing_date_opened": [
        "This account doesn't show when it was opened",
        "The date opened field is blank for this tradeline",
        "I couldn't find an account opening date on this item",
        "When did this account supposedly start? The date opened is missing",
        "This account has no opening date, which seems incomplete",
        "The original date this account was opened isn't showing",
        "There's no date opened information for this account",
        "Without a date opened, how can this account history be verified?",
    ],

    # Missing Date Last Active
    "missing_dla": [
        "This account doesn't show any recent activity date",
        "The date of last activity isn't appearing on this tradeline",
        "When was this account last active? That information is missing",
        "I don't see any date last active on this account",
        "The last activity date field is empty for this item",
        "This account has no recent activity date reported",
        "There's no indication of when this account was last used",
        "The last active date information is missing from this tradeline",
    ],

    # Impossible Timeline
    "impossible_timeline": [
        "The dates on this account don't make chronological sense",
        "Something is wrong with the timeline - the dates are out of order",
        "These dates create an impossible sequence of events",
        "The chronology of dates on this account can't be correct",
        "How can the dates work this way? The timeline is impossible",
        "The order of dates on this tradeline doesn't make sense",
        "There's a timeline problem - these dates conflict with each other",
        "The sequence of dates creates an impossible scenario",
    ],

    # Closed OC Reporting Balance
    "closed_oc_reporting_balance": [
        "This closed account is still showing a balance, which seems wrong",
        "Why does this closed original creditor account have a balance?",
        "The balance should be zero on this closed account",
        "This account was closed but still reports a balance",
        "A closed OC account shouldn't be reporting money owed",
        "This tradeline is closed yet shows an outstanding balance",
        "The balance on this closed account needs to be corrected to zero",
        "Why is a balance appearing on this closed original account?",
    ],

    # Missing Original Creditor
    "missing_original_creditor": [
        "This collection doesn't show who the original creditor was",
        "I can't verify this debt because the original creditor isn't listed",
        "Who was the original creditor? That information is missing",
        "This collection account doesn't identify the original account holder",
        "The original creditor name isn't showing on this item",
        "Without knowing the original creditor, how can I verify this debt?",
        "This debt doesn't show where it supposedly came from originally",
        "The original creditor information is missing from this collection",
    ],

    # Charge-off Missing DOFD
    "chargeoff_missing_dofd": [
        "This charge-off doesn't have a date of first delinquency",
        "The DOFD is missing from this charged-off account",
        "Without a DOFD, how is the reporting period calculated for this charge-off?",
        "This charge-off account needs to show when the delinquency started",
        "The required DOFD isn't appearing on this charged-off tradeline",
        "This charged-off account is missing the first delinquency date",
        "I don't see a DOFD on this charge-off, which is required",
        "The date of first delinquency is blank on this charge-off",
    ],

    # Closed OC Reporting Past Due
    "closed_oc_reporting_past_due": [
        "This closed account is showing a past due amount, which is incorrect",
        "Why is there a past due amount on this closed account?",
        "A closed original creditor account shouldn't show past due",
        "The past due on this closed account should be cleared",
        "This closed account incorrectly reports a past due balance",
        "Past due shouldn't appear on a closed original creditor account",
        "The past due amount on this closed account needs to be removed",
        "This account is closed but still shows money past due",
    ],

    # Balance Exceeds High Credit
    "balance_exceeds_high_credit": [
        "The balance is higher than the high credit, which isn't possible",
        "How can the current balance exceed the highest it's ever been?",
        "The balance shown is more than the high credit limit",
        "This account shows a balance above the high credit mark",
        "The balance exceeds high credit - that doesn't make sense",
        "Something's wrong - the balance is greater than high credit",
        "The current balance can't logically exceed the high credit",
        "These numbers don't work - balance shouldn't exceed high credit",
    ],

    # Negative Credit Limit
    "negative_credit_limit": [
        "This account shows a negative credit limit, which is impossible",
        "A credit limit can't be a negative number",
        "The negative credit limit on this account is clearly an error",
        "How can a credit limit be less than zero?",
        "This tradeline has a negative credit limit, which isn't valid",
        "The credit limit shown is negative, which can't be correct",
        "A minus credit limit is being reported, which makes no sense",
        "This negative credit limit needs to be corrected",
    ],

    # Cross-Bureau Discrepancy
    "cross_bureau_discrepancy": [
        "This account shows different information across my credit reports",
        "The details on this account don't match between bureaus",
        "I noticed inconsistencies when comparing this account across bureaus",
        "The information varies between credit bureaus for this account",
        "This tradeline has conflicting data depending on which report I check",
        "There are discrepancies in how this account appears across bureaus",
        "The account details are different on each credit report",
        "This item shows inconsistent information between reporting agencies",
    ],

    # Duplicate Account
    "duplicate_account": [
        "This same account appears to be listed more than once",
        "I think this is a duplicate entry on my credit report",
        "This account seems to be reported twice",
        "There appears to be a duplicate listing for this tradeline",
        "This same debt is showing up multiple times",
        "I believe this is the same account listed again",
        "This looks like a duplicate entry that should be removed",
        "The same account information appears more than once",
    ],

    # Account Not Mine
    "not_my_account": [
        "I don't recognize this account - it's not mine",
        "This account doesn't belong to me",
        "I've never had an account with this creditor",
        "This tradeline is not my account",
        "I have no record of ever opening this account",
        "This account appears to be reporting on the wrong file",
        "I don't know where this account came from - it's not mine",
        "This is someone else's account appearing on my report",
    ],

    # Incorrect Account Status
    "incorrect_status": [
        "The status on this account doesn't reflect its actual condition",
        "This account is showing the wrong status",
        "The status being reported isn't accurate",
        "This account's status needs to be corrected",
        "The reported status doesn't match the true state of this account",
        "I believe the status on this tradeline is incorrect",
        "This account is showing a status that isn't right",
        "The account status needs to be updated to reflect reality",
    ],

    # Incorrect Balance
    "incorrect_balance": [
        "The balance shown on this account isn't correct",
        "This account is reporting the wrong balance amount",
        "The balance doesn't match what I actually owe",
        "I believe the balance on this account is incorrect",
        "This isn't the right balance for this account",
        "The amount shown doesn't reflect the true balance",
        "There's an error in the balance being reported",
        "The balance on this tradeline needs to be corrected",
    ],

    # Late Payment Dispute
    "late_payment_dispute": [
        "The late payment shown on this account isn't accurate",
        "I don't believe this late payment occurred as reported",
        "This late payment mark doesn't match my records",
        "The payment history on this account shows incorrect late payments",
        "I'm disputing the late payment indicated on this tradeline",
        "This late payment shouldn't be on my record",
        "The payment was made on time but shows as late",
        "I have evidence this payment wasn't actually late",
    ],
}


# =============================================================================
# ACCOUNT REFERENCE VARIATIONS
# =============================================================================

ACCOUNT_REFERENCES = {
    "with_creditor": [
        "my {creditor} account",
        "the account with {creditor}",
        "my account with {creditor}",
        "the {creditor} tradeline",
        "this {creditor} account",
    ],
    "with_number": [
        "account {number} with {creditor}",
        "my {creditor} account (#{number})",
        "the {creditor} account ending in {number}",
        "account #{number} from {creditor}",
    ],
    "generic": [
        "this account",
        "this tradeline",
        "this item",
        "this entry",
    ],
}


# =============================================================================
# CONFIDENCE LEVEL EXPRESSIONS
# =============================================================================

CONFIDENCE_PHRASES = [
    "I believe this is incorrect",
    "This doesn't match my records",
    "This appears to be an error",
    "This is inaccurate",
    "I'm concerned this may be wrong",
    "This information isn't right",
    "I don't think this is accurate",
    "There seems to be an error here",
    "This doesn't look correct to me",
    "I question the accuracy of this",
]


# =============================================================================
# ACTION REQUEST VARIATIONS (what we want the bureau to do)
# =============================================================================

ACTION_REQUESTS = [
    "Please look into this and correct any errors",
    "I'd appreciate if you could investigate and update this",
    "Could you verify this information with the furnisher?",
    "I'm asking for this to be investigated and corrected",
    "Please review this and make any necessary corrections",
    "I request that this be verified for accuracy",
    "Would you please investigate this discrepancy?",
    "I'd like this looked into and fixed if incorrect",
    "Please verify and correct this information",
    "I'm requesting an investigation into this item",
]


# =============================================================================
# SUPPORTING EVIDENCE MENTIONS (optional inclusion)
# =============================================================================

EVIDENCE_MENTIONS = [
    "According to my records",
    "My statements show",
    "I have documentation indicating",
    "My payment history reflects",
    "Based on my records",
    "My bank statements confirm",
    "Documentation I have shows",
    "My financial records indicate",
    None,  # Sometimes don't mention evidence
    None,
    None,  # Weight towards not mentioning
]


def get_violation_expression(violation_type: str, rng) -> str:
    """Get a random expression for a violation type."""
    expressions = VIOLATION_EXPRESSIONS.get(violation_type, [])
    if not expressions:
        return f"This account has an issue that needs investigation"
    return rng.choice(expressions)


def get_account_reference(creditor_name: str, account_number: str, rng, style: str = None) -> str:
    """Get a varied account reference."""
    if style is None:
        if account_number and rng.random() > 0.5:
            style = "with_number"
        elif creditor_name:
            style = "with_creditor"
        else:
            style = "generic"

    templates = ACCOUNT_REFERENCES.get(style, ACCOUNT_REFERENCES["generic"])
    template = rng.choice(templates)

    # Handle last 4 digits of account number
    if account_number and len(account_number) >= 4:
        number = account_number[-4:]
    else:
        number = account_number or ""

    return template.format(creditor=creditor_name or "Unknown", number=number)


def get_confidence_phrase(rng) -> str:
    """Get a confidence/assertion phrase."""
    return rng.choice(CONFIDENCE_PHRASES)


def get_action_request(rng) -> str:
    """Get an action request phrase."""
    return rng.choice(ACTION_REQUESTS)


def get_evidence_mention(rng) -> str:
    """Get an optional evidence mention (may return None)."""
    return rng.choice(EVIDENCE_MENTIONS)
