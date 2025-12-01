"""
Legal Letter Generator - Diversity Engine
Provides anti-template measures: sentence diversity, synonym variation, and structure shuffling.
"""
import random
from typing import List, Dict, Tuple, Optional

# Pillar 5: Synonym tables for diversification

# Grouping strategy-specific preambles for structural differentiation
GROUPING_STRATEGY_PREAMBLES = {
    "by_fcra_section": [
        "The following violations are organized by the specific FCRA sections they breach.",
        "Each group below identifies violations of a distinct statutory provision.",
        "These disputes are categorized by the applicable legal requirement that has been violated.",
    ],
    "by_metro2_field": [
        "These items are grouped by the Metro-2 data fields that contain reporting errors.",
        "The following analysis organizes violations by affected credit reporting elements.",
        "Each category identifies specific data fields with compliance issues.",
    ],
    "by_creditor": [
        "Violations are presented by furnisher to facilitate targeted investigation.",
        "The following items are organized by the reporting entity responsible for each error.",
        "Each section addresses inaccuracies from a specific creditor or data furnisher.",
    ],
    "by_severity": [
        "These disputes are prioritized by the severity of their impact on my credit profile.",
        "Items requiring urgent attention are presented first, followed by lower-priority issues.",
        "The following violations are ranked by their potential harm to my creditworthiness.",
    ],
}

# Strategy-specific violation format templates
STRATEGY_VIOLATION_FORMATS = {
    "by_fcra_section": {
        "header_template": "Statutory Violation #{index}: {creditor}",
        "fields_order": ["violation_type", "fcra_section", "metro2_field", "evidence"],
        "emphasis": "legal",
        "summary_style": "statutory",
    },
    "by_metro2_field": {
        "header_template": "Data Element Error #{index}: {creditor}",
        "fields_order": ["metro2_field", "violation_type", "evidence", "fcra_section"],
        "emphasis": "technical",
        "summary_style": "data",
    },
    "by_creditor": {
        "header_template": "Account #{index} ({account})",
        "fields_order": ["evidence", "violation_type", "metro2_field", "fcra_section"],
        "emphasis": "account",
        "summary_style": "creditor",
    },
    "by_severity": {
        "header_template": "[{severity}] Issue #{index}: {creditor}",
        "fields_order": ["evidence", "violation_type", "metro2_field", "fcra_section"],
        "emphasis": "urgency",
        "summary_style": "priority",
    },
}

# Strategy-specific section summaries
STRATEGY_SUMMARIES = {
    "by_fcra_section": [
        "Each statutory violation documented above requires verification under the applicable FCRA provision.",
        "The legal deficiencies enumerated above are organized by the sections of federal law they violate.",
        "Your reinvestigation must address each statutory violation categorized above.",
    ],
    "by_metro2_field": [
        "The data element errors detailed above demonstrate systematic reporting failures.",
        "Each Metro-2 field discrepancy requires correction in your credit reporting systems.",
        "These technical errors in your reporting data must be corrected at the source.",
    ],
    "by_creditor": [
        "Each furnisher listed above must be contacted to verify the reported information.",
        "Your reinvestigation should address each creditor's reporting separately.",
        "The errors from each furnisher require independent verification and correction.",
    ],
    "by_severity": [
        "The prioritized issues above require attention in the order of their impact severity.",
        "High-priority items demand immediate correction due to their significant credit impact.",
        "Addressing these violations in order of severity will minimize ongoing damage to my credit profile.",
    ],
}

# Bureau-specific introductory content for differentiation
BUREAU_SPECIFIC_CONTENT = {
    "transunion": {
        "intro": [
            "As a consumer whose credit file you maintain, I am exercising my rights under federal law.",
            "Your records concerning my credit history require immediate attention.",
            "My TransUnion credit file contains data that must be reinvestigated.",
        ],
        "closing": [
            "TransUnion must comply with FCRA reinvestigation requirements within 30 days.",
            "I expect TransUnion to fulfill its statutory duties promptly.",
            "Your bureau is obligated to conduct a reasonable investigation.",
        ],
    },
    "experian": {
        "intro": [
            "Pursuant to federal law, I am disputing information in my Experian credit file.",
            "Experian is required to maintain accurate records under the FCRA.",
            "My Experian credit report contains items requiring verification.",
        ],
        "closing": [
            "Experian must complete its reinvestigation within the statutory timeframe.",
            "I demand Experian comply with its obligations under 15 U.S.C. § 1681.",
            "Your agency is required to verify or delete disputed information.",
        ],
    },
    "equifax": {
        "intro": [
            "I am formally disputing items in my Equifax credit file under the FCRA.",
            "Equifax maintains credit information about me that requires correction.",
            "As Equifax is a consumer reporting agency under federal law, you must reinvestigate.",
        ],
        "closing": [
            "Equifax is required to complete reinvestigation and notify me of results.",
            "I expect full compliance with FCRA Section 611 requirements.",
            "Your bureau must verify this information through competent sources.",
        ],
    },
}

# FCRA citation variations to avoid repetition
FCRA_CITATION_VARIANTS = {
    "611": [
        "FCRA Section 611",
        "15 U.S.C. § 1681i",
        "Section 611 of the FCRA",
        "the reinvestigation provision (Section 611)",
    ],
    "623": [
        "FCRA Section 623",
        "15 U.S.C. § 1681s-2",
        "Section 623 of the FCRA",
        "the furnisher duties provision",
    ],
    "623(a)(1)": [
        "Section 623(a)(1)",
        "15 U.S.C. § 1681s-2(a)(1)",
        "FCRA 623(a)(1)",
        "the accuracy requirement provision",
    ],
    "623(b)": [
        "Section 623(b)",
        "15 U.S.C. § 1681s-2(b)",
        "FCRA 623(b)",
        "the furnisher investigation duty",
    ],
    "607(b)": [
        "Section 607(b)",
        "15 U.S.C. § 1681e(b)",
        "FCRA 607(b)",
        "the maximum possible accuracy requirement",
    ],
    "605(a)": [
        "Section 605(a)",
        "15 U.S.C. § 1681c(a)",
        "FCRA 605(a)",
        "the obsolescence provision",
    ],
}

SYNONYMS = {
    "verify": ["confirm", "validate", "check", "review", "examine"],
    "inaccurate": ["incorrect", "erroneous", "false", "wrong", "mistaken"],
    "information": ["data", "details", "records", "entries", "items"],
    "dispute": ["challenge", "contest", "question", "object to"],
    "request": ["ask", "require", "demand", "seek"],
    "provide": ["furnish", "supply", "produce", "submit"],
    "documentation": ["documents", "records", "evidence", "paperwork"],
    "pursuant": ["under", "in accordance with", "per", "as required by"],
    "requires": ["mandates", "obligates", "compels", "necessitates"],
    "delete": ["remove", "expunge", "eliminate", "strike"],
    "immediately": ["promptly", "without delay", "forthwith", "at once"],
    "failure": ["inability", "neglect", "omission"],
    "conduct": ["perform", "carry out", "undertake", "execute"],
    "investigation": ["review", "inquiry", "examination", "probe"],
    "accurate": ["correct", "precise", "exact", "true"],
    "comply": ["conform", "adhere", "abide by", "follow"],
    "obligation": ["duty", "responsibility", "requirement"],
}

# Pillar 4: Violation intro variations by tone
VIOLATION_INTROS = {
    "strict_legal": [
        "This item is disputed as inaccurate, incomplete, or unverifiable pursuant to 15 U.S.C. § 1681i.",
        "I formally challenge the accuracy of this entry under FCRA Section 611.",
        "This reported information fails to meet FCRA accuracy standards.",
        "The accuracy of this data element is disputed under applicable federal law.",
        "This item requires verification through original source documentation.",
        "I dispute the completeness and accuracy of this reporting.",
        "This entry is contested as unverifiable under FCRA requirements.",
        "The reported data for this account is disputed as inaccurate.",
    ],
    "professional": [
        "I dispute this information as inaccurate and request verification.",
        "This item appears to be incorrect and needs to be verified.",
        "I am disputing the accuracy of this entry.",
        "This information does not match my records and should be verified.",
        "I request that you verify this item through proper documentation.",
        "This reported information appears to contain errors.",
        "I am challenging the accuracy of this data.",
        "Please verify this entry against original source documents.",
    ],
    "soft_legal": [
        "This information doesn't look right to me.",
        "I believe there's an error with this item.",
        "This doesn't match what I have in my records.",
        "I'm not sure this information is correct.",
        "Could you please check this entry for accuracy?",
        "I think there may be a mistake here.",
        "This item seems to have some problems.",
        "I'd like you to take another look at this.",
    ],
    "aggressive": [
        "This information is DISPUTED as FALSE, INACCURATE, and UNVERIFIABLE.",
        "I DEMAND immediate verification of this ERRONEOUS data.",
        "This entry represents a CLEAR VIOLATION of FCRA accuracy requirements.",
        "You are reporting INACCURATE information that MUST be corrected.",
        "This data is DISPUTED and requires IMMEDIATE investigation.",
        "Your continued reporting of this UNVERIFIED data exposes you to liability.",
        "This item is DISPUTED as fundamentally INACCURATE.",
        "This entry FAILS to meet the accuracy standards required by law.",
    ],
}

# Pillar 4: Legal basis variations for aggressive tone
AGGRESSIVE_LEGAL_BASIS = [
    "LEGAL BASIS: Your reinvestigation procedures are UNREASONABLE if you merely parrot back furnisher confirmations without independent verification.",
    "LEGAL AUTHORITY: Mere rubber-stamping of furnisher responses does NOT satisfy FCRA reinvestigation requirements.",
    "FCRA VIOLATION: Parroting furnisher data without independent review constitutes WILLFUL noncompliance.",
    "PROCEDURAL DEFICIENCY: Your reliance on furnisher confirmations alone fails to meet the reasonable reinvestigation standard.",
    "LEGAL GROUND: Simply accepting furnisher assertions WITHOUT independent verification violates established FCRA standards.",
    "REINVESTIGATION FAILURE: Deferring to furnisher responses without original documentation review is legally INSUFFICIENT.",
    "STATUTORY REQUIREMENT: FCRA mandates independent verification - not mere echo of furnisher claims.",
    "UNREASONABLE PROCEDURE: Relying solely on electronic verification from furnishers is LEGALLY DEFICIENT.",
]

# Pillar 4: Verification demand variations by tone
VERIFICATION_DEMANDS = {
    "strict_legal": [
        "I demand verification of this data through production of original source documentation, not merely furnisher confirmation.",
        "Provide original documentation establishing the accuracy of this reported information.",
        "Verification must be through primary sources, not parroted furnisher responses.",
        "Produce competent evidence supporting the accuracy of this entry.",
        "Original source documentation is required to verify this disputed item.",
        "I require production of documents proving the accuracy of this data.",
    ],
    "professional": [
        "Please verify this through original source documentation.",
        "I request verification through proper documentation rather than furnisher confirmation.",
        "Please obtain original documents to verify this information.",
        "Verification should be through independent documentation.",
        "I ask that you verify this with original records.",
        "Please confirm this information against primary source documents.",
    ],
    "soft_legal": [
        "Could you please verify it with the original documents?",
        "I'd appreciate it if you could check the original records.",
        "Please look into this and verify it's accurate.",
        "Can you confirm this with the original creditor's records?",
        "I'm asking that you verify this information is correct.",
        "Please check the documentation to make sure this is right.",
    ],
    "aggressive": [
        "You are REQUIRED to verify this through original source documentation - NOT through the same furnisher that provided the erroneous data.",
        "VERIFICATION MUST BE THROUGH PRIMARY DOCUMENTATION - furnisher parroting is LEGALLY INSUFFICIENT.",
        "I DEMAND original documentation - NOT mere confirmation from the reporting entity.",
        "Your verification MUST utilize original source records - ANYTHING LESS is unreasonable.",
        "Produce COMPETENT EVIDENCE or DELETE this disputed information.",
        "ORIGINAL DOCUMENTS are REQUIRED - electronic verification alone is INSUFFICIENT.",
    ],
}


def sentence_similarity(a: str, b: str) -> float:
    """Calculate word-overlap similarity between two sentences."""
    a_tokens = set(a.lower().split())
    b_tokens = set(b.lower().split())
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens & b_tokens)
    denom = min(len(a_tokens), len(b_tokens))
    return overlap / max(1, denom)


def enforce_sentence_diversity(sentences: List[str], threshold: float = 0.70) -> List[str]:
    """Remove near-duplicate sentences from a list."""
    unique = []
    for s in sentences:
        s_stripped = s.strip()
        if not s_stripped:
            unique.append(s)
            continue
        if all(sentence_similarity(s_stripped, u.strip()) < threshold for u in unique if u.strip()):
            unique.append(s)
    return unique


def diversify_text(text: str, rng: random.Random, intensity: float = 0.3) -> str:
    """Apply synonym substitution to diversify text."""
    words = text.split()
    result = []

    for word in words:
        word_lower = word.lower().rstrip('.,;:!?')
        punctuation = ''
        if word and word[-1] in '.,;:!?':
            punctuation = word[-1]
            word = word[:-1]

        if word_lower in SYNONYMS and rng.random() < intensity:
            replacement = rng.choice(SYNONYMS[word_lower])
            # Preserve capitalization
            if word and word[0].isupper():
                replacement = replacement.capitalize()
            if word.isupper():
                replacement = replacement.upper()
            result.append(replacement + punctuation)
        else:
            result.append(word + punctuation if punctuation and not word.endswith(punctuation) else (word if not punctuation else word + punctuation))

    return ' '.join(result)


def get_violation_intro(tone: str, rng: random.Random) -> str:
    """Get a randomized violation intro for the given tone."""
    intros = VIOLATION_INTROS.get(tone, VIOLATION_INTROS["professional"])
    return rng.choice(intros)


def get_verification_demand(tone: str, rng: random.Random) -> str:
    """Get a randomized verification demand for the given tone."""
    demands = VERIFICATION_DEMANDS.get(tone, VERIFICATION_DEMANDS["professional"])
    return rng.choice(demands)


def shuffle_section_order(sections: List[Tuple[str, any]], seed: int, preserve_positions: List[int] = None) -> List[Tuple[str, any]]:
    """
    Shuffle middle sections while preserving header/footer positions.

    Args:
        sections: List of (section_name, section_content) tuples
        seed: Random seed for consistent shuffling
        preserve_positions: Indices of sections to keep in place (default: first and last 2)
    """
    if len(sections) <= 4:
        return sections

    if preserve_positions is None:
        preserve_positions = [0, 1, len(sections) - 2, len(sections) - 1]

    rng = random.Random(seed)

    # Separate preserved and shuffleable sections
    preserved = {i: sections[i] for i in preserve_positions if i < len(sections)}
    shuffleable = [s for i, s in enumerate(sections) if i not in preserved]

    # Shuffle middle sections
    rng.shuffle(shuffleable)

    # Reconstruct
    result = []
    shuffle_idx = 0
    for i in range(len(sections)):
        if i in preserved:
            result.append(preserved[i])
        else:
            result.append(shuffleable[shuffle_idx])
            shuffle_idx += 1

    return result


def get_diverse_paragraph_start(tone: str, section_type: str, rng: random.Random) -> str:
    """Get a diverse paragraph start to avoid repetitive intros."""
    starters = {
        "violations": {
            "strict_legal": [
                "Upon review, the following deficiency was identified:",
                "Analysis of my credit file reveals the following issue:",
                "Examination of the reported data shows:",
                "The following inaccuracy has been identified:",
                "Review of my report indicates:",
            ],
            "professional": [
                "I found the following issue:",
                "My review identified:",
                "The following item appears incorrect:",
                "I noticed an error with:",
                "This entry needs attention:",
            ],
            "soft_legal": [
                "I noticed a problem with:",
                "There seems to be an issue with:",
                "I found something that doesn't look right:",
                "I'm concerned about:",
                "I'd like to point out:",
            ],
            "aggressive": [
                "The following VIOLATION has been identified:",
                "This item represents a CLEAR DEFICIENCY:",
                "The following INACCURACY requires IMMEDIATE correction:",
                "This entry is DISPUTED:",
                "The following ERROR must be addressed:",
            ],
        },
        "demands": {
            "strict_legal": [
                "Pursuant to applicable law, you are required to:",
                "Under FCRA requirements, you must:",
                "Your legal obligations include:",
                "Federal law mandates that you:",
                "The following actions are legally required:",
            ],
            "professional": [
                "I request that you:",
                "Please take the following actions:",
                "I am asking that you:",
                "The following steps should be taken:",
                "I would like you to:",
            ],
            "soft_legal": [
                "I'm hoping you can:",
                "It would help if you could:",
                "I'd appreciate it if you would:",
                "Would you please:",
                "I'm asking that you:",
            ],
            "aggressive": [
                "I DEMAND the following actions:",
                "You MUST take these steps:",
                "The following is REQUIRED:",
                "You are OBLIGATED to:",
                "IMMEDIATE action is required:",
            ],
        },
    }

    section_starters = starters.get(section_type, {})
    tone_starters = section_starters.get(tone, section_starters.get("professional", ["Regarding:"]))
    return rng.choice(tone_starters)


class DiversityEngine:
    """Main diversity engine that coordinates all anti-template measures."""

    def __init__(self, seed: int = None, tone: str = "professional"):
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.tone = tone
        self.rng = random.Random(self.seed)
        self._used_intros = set()
        self._used_demands = set()
        self._used_legal_basis = set()

    def get_unique_violation_intro(self) -> str:
        """Get a violation intro that hasn't been used yet."""
        intros = VIOLATION_INTROS.get(self.tone, VIOLATION_INTROS["professional"])
        available = [i for i in intros if i not in self._used_intros]
        if not available:
            self._used_intros.clear()
            available = intros

        intro = self.rng.choice(available)
        self._used_intros.add(intro)
        return intro

    def get_unique_verification_demand(self) -> str:
        """Get a verification demand that hasn't been used yet."""
        demands = VERIFICATION_DEMANDS.get(self.tone, VERIFICATION_DEMANDS["professional"])
        available = [d for d in demands if d not in self._used_demands]
        if not available:
            self._used_demands.clear()
            available = demands

        demand = self.rng.choice(available)
        self._used_demands.add(demand)
        return demand

    def get_unique_legal_basis(self) -> str:
        """Get a unique legal basis statement for aggressive tone."""
        available = [b for b in AGGRESSIVE_LEGAL_BASIS if b not in self._used_legal_basis]
        if not available:
            self._used_legal_basis.clear()
            available = AGGRESSIVE_LEGAL_BASIS

        basis = self.rng.choice(available)
        self._used_legal_basis.add(basis)
        return basis

    def get_bureau_intro(self, bureau: str) -> str:
        """Get a bureau-specific intro sentence."""
        bureau_lower = bureau.lower()
        content = BUREAU_SPECIFIC_CONTENT.get(bureau_lower, BUREAU_SPECIFIC_CONTENT.get("transunion"))
        return self.rng.choice(content["intro"])

    def get_bureau_closing(self, bureau: str) -> str:
        """Get a bureau-specific closing sentence."""
        bureau_lower = bureau.lower()
        content = BUREAU_SPECIFIC_CONTENT.get(bureau_lower, BUREAU_SPECIFIC_CONTENT.get("transunion"))
        return self.rng.choice(content["closing"])

    def get_strategy_preamble(self, strategy: str) -> str:
        """Get a strategy-specific preamble for structural differentiation."""
        from .diversity import GROUPING_STRATEGY_PREAMBLES
        preambles = GROUPING_STRATEGY_PREAMBLES.get(strategy, GROUPING_STRATEGY_PREAMBLES.get("by_fcra_section"))
        return self.rng.choice(preambles)

    def get_strategy_format(self, strategy: str) -> Dict:
        """Get strategy-specific violation formatting configuration."""
        from .diversity import STRATEGY_VIOLATION_FORMATS
        return STRATEGY_VIOLATION_FORMATS.get(strategy, STRATEGY_VIOLATION_FORMATS.get("by_fcra_section"))

    def get_strategy_summary(self, strategy: str) -> str:
        """Get a strategy-specific summary for the violations section."""
        from .diversity import STRATEGY_SUMMARIES
        summaries = STRATEGY_SUMMARIES.get(strategy, STRATEGY_SUMMARIES.get("by_fcra_section"))
        return self.rng.choice(summaries)

    def format_violation_header(self, strategy: str, index: int, violation: Dict) -> str:
        """Format a violation header based on strategy."""
        fmt = self.get_strategy_format(strategy)
        template = fmt.get("header_template", "Item #{index}: {creditor}")

        creditor = violation.get("creditor_name", "Unknown")
        account = violation.get("account_number_masked", "")
        severity = violation.get("severity", "medium").upper()

        return template.format(
            index=index,
            creditor=creditor,
            account=account if account else "N/A",
            severity=severity
        )

    def get_fcra_citation(self, section: str) -> str:
        """Get a varied FCRA citation for a section."""
        from .fcra_statutes import resolve_statute

        # Normalize section format
        section_key = section.replace("(", "").replace(")", "").replace(" ", "")

        # Try exact match first
        if section in FCRA_CITATION_VARIANTS:
            return self.rng.choice(FCRA_CITATION_VARIANTS[section])

        # Try normalized match
        for key, variants in FCRA_CITATION_VARIANTS.items():
            if section_key in key.replace("(", "").replace(")", ""):
                return self.rng.choice(variants)

        # Fallback: use the authoritative SSOT resolver for correct USC citation
        return resolve_statute(section)

    def diversify(self, text: str, intensity: float = 0.3) -> str:
        """Apply synonym diversification to text."""
        return diversify_text(text, self.rng, intensity)

    def get_paragraph_start(self, section_type: str) -> str:
        """Get a diverse paragraph start."""
        return get_diverse_paragraph_start(self.tone, section_type, self.rng)

    def filter_duplicate_sentences(self, text: str, threshold: float = 0.70) -> str:
        """Remove near-duplicate sentences from text."""
        lines = text.split('\n')
        filtered = enforce_sentence_diversity(lines, threshold)
        return '\n'.join(filtered)
