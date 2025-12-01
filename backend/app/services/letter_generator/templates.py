"""
Credit Copilot - Template Seeds for Letter Generation

Contains rotating phrase banks for:
- Opening paragraphs (15+ variations)
- Context seeds (why reviewing report)
- Transitions between violations
- Closing paragraphs (15+ variations)
- Signature variations

Key principle: Seeds rotate and are tracked per consumer to prevent
consecutive reuse within 10 letters.
"""
from typing import Dict, List


# =============================================================================
# OPENING SEEDS - 15+ variations per tone
# =============================================================================

OPENINGS: Dict[str, List[str]] = {
    "formal": [
        "I am writing to formally dispute certain information appearing on my credit report that I believe to be inaccurate.",
        "Please accept this letter as my formal request to investigate and correct errors I have identified on my credit report.",
        "I have recently reviewed my credit report and identified several items that require investigation and correction.",
        "This letter constitutes a formal dispute of inaccurate information currently appearing on my credit report.",
        "After careful review of my credit report, I am writing to dispute items that do not accurately reflect my credit history.",
        "I am exercising my right to dispute inaccurate credit information and request an investigation into the following items.",
        "Please consider this my formal notification that I dispute the accuracy of certain items on my credit report.",
        "I am submitting this dispute regarding information on my credit report that I have determined to be incorrect.",
        "This correspondence serves as my formal dispute of credit report entries that contain errors.",
        "I am writing to bring to your attention inaccuracies on my credit report that require correction.",
        "Please investigate the following disputed items on my credit report as required under federal law.",
        "I am disputing specific items on my credit report that do not accurately represent my credit history.",
        "This letter serves as documentation of my dispute regarding errors contained in my credit report.",
        "I have identified errors on my credit report and am formally requesting an investigation.",
        "Please accept this as my written dispute regarding inaccurate entries on my credit file.",
    ],

    "assertive": [
        "I demand immediate investigation and correction of the following errors on my credit report.",
        "The following information on my credit report is incorrect and must be corrected without delay.",
        "I am disputing these items and expect them to be properly investigated and corrected.",
        "These errors on my credit report are unacceptable and need to be fixed immediately.",
        "I require that you investigate and correct the following inaccurate information.",
        "The errors I've found on my credit report must be addressed and corrected promptly.",
        "I insist on a thorough investigation of these inaccurate items on my credit report.",
        "These credit report errors are damaging my financial standing and must be corrected.",
        "I am formally disputing these items and expect swift action to correct them.",
        "The following items are being reported incorrectly and this needs to be resolved.",
        "I demand verification of these items as they are clearly inaccurate.",
        "These reporting errors need immediate attention and correction.",
        "I expect these disputes to be handled seriously and resolved quickly.",
        "The inaccuracies I've identified must be investigated and removed or corrected.",
        "I will not accept continued reporting of this incorrect information.",
    ],

    "conversational": [
        "I recently checked my credit report and found some things that don't look right.",
        "After looking over my credit report, I noticed a few errors I'd like to get fixed.",
        "I've been reviewing my credit and found some information that seems incorrect.",
        "I wanted to reach out because I spotted some errors on my credit report.",
        "While checking my credit recently, I found some things that need to be corrected.",
        "I'm writing because my credit report has some information that isn't accurate.",
        "I've noticed some problems with my credit report that I hope you can help me fix.",
        "I found a few errors when I looked at my credit report and wanted to bring them up.",
        "There are some things on my credit report that don't match my records.",
        "I'm reaching out about some credit report errors I'd like investigated.",
        "I've discovered some inaccuracies on my credit report that concern me.",
        "My credit report seems to have some mistakes I'd like your help correcting.",
        "I went through my credit report and found items that don't seem right.",
        "I'm hoping you can help me with some errors I found on my credit report.",
        "After reviewing my credit, I have some concerns about certain entries.",
    ],

    "narrative": [
        "I want to share what I discovered when I recently reviewed my credit report.",
        "Let me explain the issues I found while going through my credit report.",
        "After reviewing my credit report, I need to bring some concerns to your attention.",
        "I've been working on improving my credit and found some errors I need to address.",
        "When I pulled my credit report, I was surprised to find several inaccuracies.",
        "I've been carefully managing my finances and noticed problems with my credit report.",
        "While preparing for a major financial decision, I reviewed my credit and found errors.",
        "I recently went through my credit report and discovered information that concerns me.",
        "Let me tell you about the issues I've identified on my credit report.",
        "I'm writing today because of what I found when checking my credit report.",
        "During my regular review of my credit, I came across some troubling errors.",
        "I need to explain the problems I've discovered with my credit report.",
        "When I checked my credit recently, I found things that didn't make sense.",
        "I want to describe the inaccuracies I've found on my credit report.",
        "Here's what I discovered when I examined my credit report carefully.",
    ],
}


# =============================================================================
# CONTEXT SEEDS - Why the consumer is reviewing their report
# =============================================================================

CONTEXT_SEEDS = [
    "While preparing to apply for a mortgage",
    "As I was reviewing my annual free credit report",
    "While planning for a major purchase",
    "After being unexpectedly denied credit",
    "During my regular monitoring of my credit",
    "While working on improving my financial health",
    "As part of my annual financial review",
    "While preparing for a car loan application",
    "After noticing something odd on a credit monitoring alert",
    "While refinancing my home",
    "As I was checking my credit before a big decision",
    "During my quarterly credit check",
    "While getting my finances in order",
    "After receiving a notice about my credit",
    None,  # Sometimes no context is given
    None,
    None,  # Weight towards not always including context
]


# =============================================================================
# TRANSITIONS BETWEEN VIOLATIONS
# =============================================================================

TRANSITIONS = {
    "to_next": [
        "Additionally,",
        "I also noticed that",
        "Another concern is",
        "Furthermore,",
        "There's also an issue with",
        "I also want to point out that",
        "In addition,",
        "I also found that",
        "Similarly,",
        "Along with the above,",
        "Another item that concerns me is",
        "I'd also like to address",
        "Moving on,",
        "Next,",
        "There's another problem with",
    ],

    "grouping": [
        "Regarding the accounts with {creditor}:",
        "As for my {creditor} accounts:",
        "Looking at {creditor}:",
        "Concerning the {creditor} tradeline:",
        "With respect to {creditor}:",
    ],

    "continuation": [
        "This account also has another issue -",
        "On this same account,",
        "For this same tradeline,",
        "Additionally, this account shows",
        "This same item also has",
    ],
}


# =============================================================================
# CLOSING SEEDS - 15+ variations per tone
# =============================================================================

CLOSINGS: Dict[str, List[str]] = {
    "formal": [
        "Please investigate these items and provide me with the results within 30 days as required by federal law.",
        "I request that you investigate these items and provide written notification of the results.",
        "Please conduct a thorough investigation and correct any verified errors on my credit report.",
        "I expect a response within the timeframe mandated by the Fair Credit Reporting Act.",
        "Please update my credit report accordingly and send me a corrected copy.",
        "I trust you will handle this dispute with the attention it deserves.",
        "Please verify these items with the furnishers and correct any inaccuracies.",
        "I look forward to receiving your response and updated credit report.",
        "Please ensure these items are properly investigated and corrected as appropriate.",
        "I request written confirmation once your investigation is complete.",
        "Please remove or correct these items and notify me of the outcome.",
        "I expect these disputes to be resolved within the legally required timeframe.",
        "Please investigate and respond with your findings as required by law.",
        "I await your response and correction of these inaccurate items.",
        "Please handle this matter promptly and send confirmation of any changes.",
    ],

    "assertive": [
        "I expect these items to be corrected or removed within the legally mandated timeframe.",
        "Failure to properly investigate may result in further action on my part.",
        "I require written confirmation that these items have been investigated and corrected.",
        "These errors must be addressed immediately to bring my report into compliance.",
        "I expect prompt action to resolve these inaccuracies.",
        "I will follow up if these items are not properly addressed.",
        "I demand that these errors be fixed and my credit report be updated.",
        "I expect a full investigation and correction of all disputed items.",
        "These matters require your immediate attention and resolution.",
        "I insist on a thorough investigation of every item listed above.",
        "I expect these corrections to be made without further delay.",
        "I require that you take these disputes seriously and act accordingly.",
        "Failure to correct these errors will necessitate additional measures.",
        "I expect you to fulfill your legal obligations regarding this dispute.",
        "I will be monitoring my credit report to ensure these corrections are made.",
    ],

    "conversational": [
        "Thanks for looking into this for me. I appreciate your help.",
        "I'd really appreciate you checking on these items and fixing any errors.",
        "Please let me know what you find out. Thank you for your help.",
        "I look forward to hearing back from you about this.",
        "Thanks in advance for your help getting this sorted out.",
        "I appreciate you taking the time to investigate these issues.",
        "Please get back to me with what you discover. Thanks!",
        "I'm hoping we can get these issues resolved soon.",
        "Thank you for helping me with these credit report problems.",
        "I'd appreciate an update once you've had a chance to look into this.",
        "Thanks for your attention to this matter.",
        "I hope we can work together to fix these errors.",
        "Looking forward to your response. Thank you.",
        "I appreciate any help you can provide with these issues.",
        "Thanks for taking care of this for me.",
    ],

    "narrative": [
        "I hope this explanation helps you understand why these items need to be investigated.",
        "I trust you'll see why I'm concerned about these errors and investigate them thoroughly.",
        "Thank you for taking the time to review my situation.",
        "I look forward to hearing back from you about what you find.",
        "I hope you can help me resolve these issues with my credit report.",
        "I appreciate your understanding and help with these matters.",
        "Please let me know what your investigation reveals.",
        "I'm counting on you to help me get these errors corrected.",
        "Thank you for considering my concerns and looking into these items.",
        "I hope my explanation makes clear why these items need attention.",
        "I trust you'll investigate these matters fairly and thoroughly.",
        "I look forward to having these issues resolved.",
        "Thank you for your time and attention to my credit report concerns.",
        "I hope we can work together to correct my credit report.",
        "I appreciate your help in getting to the bottom of these issues.",
    ],
}


# =============================================================================
# SIGNATURE VARIATIONS
# =============================================================================

SIGNATURES = [
    "Sincerely,",
    "Respectfully,",
    "Thank you,",
    "Regards,",
    "Best regards,",
    "Yours truly,",
    "With appreciation,",
]


# =============================================================================
# SUBJECT LINE VARIATIONS
# =============================================================================

SUBJECT_LINES = [
    "RE: Credit Report Dispute",
    "RE: Request for Investigation",
    "RE: Dispute of Credit Report Items",
    "Subject: Credit Report Dispute",
    "RE: Formal Dispute Notice",
    "Subject: Request for Credit Report Investigation",
    "RE: Dispute - Inaccurate Information",
    "Subject: Credit File Dispute",
]


# =============================================================================
# CONSUMER ID INTRO VARIATIONS
# =============================================================================

CONSUMER_ID_INTROS = [
    "For identification purposes:",
    "To help you locate my file:",
    "My identification information:",
    "Please use the following to find my credit file:",
    "For reference, my information is:",
    "My personal information for identification:",
    "To locate my credit report:",
    "Here is my identifying information:",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_opening(tone: str, rng, exclude: List[str] = None) -> str:
    """Get a random opening phrase, optionally excluding recently used ones."""
    openings = OPENINGS.get(tone, OPENINGS["conversational"])
    if exclude:
        available = [o for o in openings if o not in exclude]
        if available:
            return rng.choice(available)
    return rng.choice(openings)


def get_context(rng) -> str:
    """Get a random context seed (may return None)."""
    return rng.choice(CONTEXT_SEEDS)


def get_transition(transition_type: str, rng, creditor: str = None) -> str:
    """Get a transition phrase."""
    transitions = TRANSITIONS.get(transition_type, TRANSITIONS["to_next"])
    template = rng.choice(transitions)
    if "{creditor}" in template and creditor:
        return template.format(creditor=creditor)
    return template


def get_closing(tone: str, rng, exclude: List[str] = None) -> str:
    """Get a random closing phrase, optionally excluding recently used ones."""
    closings = CLOSINGS.get(tone, CLOSINGS["conversational"])
    if exclude:
        available = [c for c in closings if c not in exclude]
        if available:
            return rng.choice(available)
    return rng.choice(closings)


def get_signature(rng) -> str:
    """Get a random signature phrase."""
    return rng.choice(SIGNATURES)


def get_subject_line(rng) -> str:
    """Get a random subject line."""
    return rng.choice(SUBJECT_LINES)


def get_consumer_id_intro(rng) -> str:
    """Get a consumer identification intro phrase."""
    return rng.choice(CONSUMER_ID_INTROS)
