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
        "This account is missing the Date of First Delinquency (DOFD) in Metro 2 Field 25",
        "The Date of First Delinquency is not reported for this account. This field is required for derogatory accounts",
        "Metro 2 Field 25 (DOFD) is blank. Without DOFD, the 7-year reporting period cannot be calculated",
        "This derogatory account has no Date of First Delinquency. The reporting period is unverifiable",
        "The DOFD field is missing from this tradeline. This violates Metro 2 reporting requirements",
        "No Date of First Delinquency is reported. This record is incomplete",
        "This account lacks Metro 2 Field 25 (DOFD). The 7-year limit cannot be determined",
        "The required DOFD information is not present on this derogatory account",
        "DOFD is missing. Without this date, the account's compliance with §605(c)(1) is unverifiable",
        "This negative account has no DOFD reported. The 7-year reporting period cannot be verified",
    ],

    # Stale/Outdated Data
    "stale_reporting": [
        "This account has not been updated in over 90 days. The data is stale",
        "The last report date on this account is outdated. This tradeline requires a current update",
        "This account information is stale. The furnisher has not reported recent data",
        "This tradeline contains old data that has not been verified recently",
        "This account was last reported over 90 days ago. The information is not current",
        "The account data is outdated. No recent updates have been reported to the bureau",
        "This tradeline is stale. The account has not been updated within the required reporting period",
        "The reporting date indicates this account information is not current",
        "This account has not been updated recently. The data cannot be verified as accurate",
        "The account information is outdated. Furnishers must report current, accurate data",
    ],

    # Missing Scheduled Payment
    "missing_scheduled_payment": [
        "This account is missing the Scheduled Monthly Payment field",
        "The Scheduled Payment amount is not reported for this tradeline",
        "This account has no monthly payment amount listed. This field is required",
        "The payment information is incomplete. The scheduled payment field is blank",
        "No scheduled payment is reported on this account. This data is missing",
        "This tradeline lacks the required payment amount information",
        "The Scheduled Payment field is blank. This record is incomplete",
        "Monthly payment amount is not reported. Payment terms cannot be verified",
        "This account does not report a scheduled payment amount",
        "The payment amount field is missing from this tradeline",
    ],

    # Obsolete Account (beyond 7-year limit)
    "obsolete_account": [
        "This account has exceeded the 7-year reporting limit under FCRA §605(a)",
        "Based on the DOFD, this account's 7-year reporting period has expired",
        "This account is past the legal reporting limit. It must be deleted under §605(a)",
        "The 7-year period for this account has passed. This item is obsolete",
        "This tradeline is obsolete. The reporting period ended based on the DOFD",
        "This account has exceeded the maximum reporting period. Deletion is required",
        "Based on the Date of First Delinquency, this item is past the 7-year limit",
        "This account is obsolete under FCRA §605(a). The reporting period has expired",
        "The 7-year reporting period has ended for this account. It must be removed",
        "This item is past its legal reporting period based on the DOFD",
    ],

    # Negative Balance
    "negative_balance": [
        "This account reports a negative balance. Negative balances are invalid under Metro 2 standards",
        "The balance field shows a negative value. This is invalid data",
        "A negative balance is reported on this account. This violates Metro 2 reporting requirements",
        "The balance is negative. Balances cannot be below zero",
        "This tradeline reports a balance below zero. This is mathematically invalid",
        "The negative balance on this account is an error. Balances must be non-negative",
        "A minus balance is being reported. This is invalid Metro 2 data",
        "The balance field contains a negative value. This data is incorrect",
    ],

    # Past Due Exceeds Balance
    "past_due_exceeds_balance": [
        "The past due amount exceeds the total balance. This is mathematically impossible",
        "Field 17B (past due) is greater than Field 17A (balance). This data is invalid",
        "The past due amount is larger than the balance. This is a data error",
        "This account shows past due greater than balance. This is mathematically impossible",
        "The past due exceeds the balance. Past due cannot exceed total balance",
        "The past due amount is larger than the total owed. This is incorrect",
        "Past due exceeds balance on this account. This is invalid data",
        "The past due and balance figures are inconsistent. Past due cannot exceed balance",
    ],

    # Future Date
    "future_date": [
        "This account contains a date in the future. Future dates are invalid",
        "A future date is being reported. This indicates unverified data",
        "This account shows a date that has not yet occurred. This is invalid",
        "A date in the future is reported on this tradeline. This is an error",
        "The dates on this account include a future date. This data is unverified",
        "This tradeline contains an impossible future date",
        "A future date is present on this account. Future dates violate reporting standards",
        "This account has a date that has not occurred. This is invalid information",
    ],

    # Missing Date Opened
    "missing_date_opened": [
        "This account is missing the Date Opened field. This field is required",
        "The Date Opened field is blank for this tradeline. This data is incomplete",
        "No account opening date is reported on this item. This is a required field",
        "The Date Opened is not reported. Account history cannot be verified",
        "This account has no opening date. This record is incomplete",
        "The Date Opened field is missing from this tradeline",
        "No Date Opened is reported for this account. This is required Metro 2 data",
        "Without a Date Opened, the account history is unverifiable",
    ],

    # Missing Date Last Active
    "missing_dla": [
        "This account is missing the Date Last Activity field",
        "The Date Last Activity is not reported on this tradeline",
        "This account has no recent activity date reported. The data is incomplete",
        "The Date Last Activity field is blank for this item",
        "No Date Last Activity is reported on this account",
        "This tradeline lacks the Date Last Activity field",
        "The Date Last Activity is missing. Account activity cannot be verified",
        "This account does not report a Date Last Activity",
    ],

    # Impossible Timeline
    "impossible_timeline": [
        "The dates on this account create an impossible chronology",
        "The timeline on this account is logically impossible. The dates conflict",
        "These dates form an impossible sequence of events",
        "The chronology of dates on this account is invalid",
        "The dates on this tradeline are in an impossible order",
        "The date sequence on this account is logically impossible",
        "The timeline is invalid. These dates cannot occur in this order",
        "The dates create an impossible scenario. This data is incorrect",
    ],

    # Closed OC Reporting Balance
    "closed_oc_reporting_balance": [
        "This closed original creditor account is reporting a balance. Closed OC accounts should report $0",
        "A balance is being reported on this closed OC account. This is incorrect",
        "This closed account reports a balance. If the debt was transferred, balance should be $0",
        "This account is closed but still reports a balance. This is invalid",
        "A closed OC account is reporting an outstanding balance. Only current debt holders may report balances",
        "This tradeline is closed but shows a balance. This is incorrect for OC accounts",
        "The balance on this closed OC account should be $0",
        "This closed original creditor account incorrectly reports a balance",
    ],

    # Missing Original Creditor
    "missing_original_creditor": [
        "This collection account does not identify the original creditor. This field is required",
        "The original creditor is not reported. Debt verification is impossible",
        "This collection is missing the original creditor name. This is a required field",
        "No original creditor is identified on this collection account",
        "The original creditor field is blank. This debt cannot be verified",
        "Without the original creditor name, this debt is unverifiable",
        "This collection does not report the original creditor. This field is required",
        "The original creditor information is missing from this collection account",
    ],

    # Charge-off Missing DOFD
    "chargeoff_missing_dofd": [
        "This charge-off account is missing the Date of First Delinquency. DOFD is required for charge-offs",
        "The DOFD is not reported on this charged-off account. This is a required field",
        "Without DOFD, the 7-year reporting period cannot be calculated for this charge-off",
        "This charge-off account lacks the required DOFD field",
        "Metro 2 Field 25 (DOFD) is missing on this charge-off. This is required",
        "This charged-off account does not report the Date of First Delinquency",
        "DOFD is missing on this charge-off. The 7-year limit cannot be verified",
        "The Date of First Delinquency field is blank on this charge-off",
    ],

    # Closed OC Reporting Past Due
    "closed_oc_reporting_past_due": [
        "This closed account is reporting a past due amount. Closed OC accounts should report $0 past due",
        "A past due amount is reported on this closed OC account. This is incorrect",
        "This closed original creditor account incorrectly shows a past due balance",
        "The past due on this closed account should be $0",
        "This closed account reports a past due balance. This is invalid for closed OC accounts",
        "Past due is reported on a closed original creditor account. This is incorrect",
        "The past due amount on this closed OC account is invalid",
        "This account is closed but shows past due. This data is incorrect",
    ],

    # Balance Exceeds High Credit
    "balance_exceeds_high_credit": [
        "The balance exceeds the high credit amount. This is mathematically impossible",
        "Current balance is greater than high credit. This data is invalid",
        "The balance is higher than the high credit. This is an error",
        "This account shows balance greater than high credit. This is impossible",
        "Balance exceeds high credit on this account. This is invalid data",
        "The balance cannot logically exceed the high credit amount",
        "Balance is greater than high credit. These figures are inconsistent",
        "The balance-to-high-credit relationship is mathematically invalid",
    ],

    # Negative Credit Limit
    "negative_credit_limit": [
        "This account reports a negative credit limit. Negative credit limits are invalid",
        "A negative credit limit is being reported. Credit limits cannot be negative",
        "The credit limit is negative on this account. This is invalid data",
        "A credit limit below zero is reported. This is impossible",
        "This tradeline has a negative credit limit. This violates Metro 2 standards",
        "The credit limit shown is negative. Credit limits must be non-negative",
        "A minus credit limit is being reported. This is invalid",
        "The negative credit limit on this account is incorrect. Credit limits cannot be negative",
    ],

    # Cross-Bureau Discrepancy
    "cross_bureau_discrepancy": [
        "This account shows different information across credit bureaus. The data is inconsistent",
        "The details on this account do not match between bureaus",
        "This account has conflicting data across credit reports",
        "The information varies between credit bureaus for this account. This is inconsistent",
        "This tradeline has conflicting data depending on which bureau is reporting",
        "There are discrepancies in how this account is reported across bureaus",
        "The account details differ between credit reports. This data is inconsistent",
        "This item shows inconsistent information between reporting agencies",
    ],

    # Duplicate Account
    "duplicate_account": [
        "This account is listed more than once. This is a duplicate entry",
        "This is a duplicate entry on my credit report",
        "This account is reported twice. One entry should be removed",
        "This is a duplicate listing for this tradeline",
        "This debt is being reported multiple times. This is incorrect",
        "This is the same account listed again. Duplicate entries are invalid",
        "This is a duplicate entry that should be removed",
        "The same account information is reported more than once",
    ],

    # Account Not Mine
    "not_my_account": [
        "This account does not belong to me. I have no record of this account",
        "This account is not mine. I have never had an account with this creditor",
        "I have no account with this creditor. This account is not mine",
        "This tradeline is not my account. I did not open this account",
        "I have no record of opening this account. This is not my account",
        "This account is on the wrong credit file. It does not belong to me",
        "This account is not mine. I have no knowledge of this account",
        "This is not my account. It is being reported in error",
    ],

    # Incorrect Account Status
    "incorrect_status": [
        "The status on this account is incorrect. The actual status differs",
        "This account is reporting the wrong status",
        "The status being reported is inaccurate",
        "This account's status is incorrect and needs correction",
        "The reported status does not match the actual state of this account",
        "The status on this tradeline is incorrect",
        "This account is reporting an incorrect status",
        "The account status is wrong. It needs to be corrected",
    ],

    # Incorrect Balance
    "incorrect_balance": [
        "The balance shown on this account is incorrect",
        "This account is reporting the wrong balance amount",
        "The balance does not match the actual amount owed",
        "The balance on this account is incorrect",
        "This is not the correct balance for this account",
        "The amount shown does not reflect the actual balance",
        "The balance being reported is incorrect",
        "The balance on this tradeline is wrong. It needs correction",
    ],

    # Late Payment Dispute
    "late_payment_dispute": [
        "The late payment shown on this account is inaccurate",
        "This late payment did not occur as reported",
        "This late payment mark does not match my records",
        "The payment history on this account shows incorrect late payments",
        "The late payment indicated on this tradeline is incorrect",
        "This late payment should not be on my record. Payment was made on time",
        "The payment was made on time but is reported as late",
        "This payment was not late. The late payment mark is incorrect",
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
    "This is incorrect",
    "This does not match my records",
    "This is an error",
    "This is inaccurate",
    "This information is wrong",
    "This information is incorrect",
    "This is not accurate",
    "There is an error here",
    "This is incorrect data",
    "The accuracy of this data is in question",
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
