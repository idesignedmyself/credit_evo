"""
Mutation Engine - Handles sentence-level transformations for letter diversity.
Includes synonym replacement, clause flipping, prepositional reshuffling, and rhetorical variants.
"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import re

from .entropy import EntropyController


@dataclass
class MutationResult:
    """Result of a mutation operation."""
    text: str
    mutations_applied: List[str]
    mutation_count: int


class SynonymEngine:
    """Handles synonym replacements while maintaining domain appropriateness."""

    # Legal domain synonyms - maintain formal register
    LEGAL_SYNONYMS: Dict[str, List[str]] = {
        "request": ["demand", "require", "seek", "petition for", "formally request"],
        "provide": ["furnish", "supply", "deliver", "produce", "make available"],
        "verify": ["confirm", "validate", "substantiate", "authenticate", "corroborate"],
        "investigate": ["examine", "review", "scrutinize", "analyze", "look into"],
        "accurate": ["correct", "precise", "exact", "truthful", "factual"],
        "inaccurate": ["incorrect", "erroneous", "false", "mistaken", "wrong"],
        "information": ["data", "details", "records", "documentation", "particulars"],
        "report": ["file", "record", "document", "statement", "account"],
        "immediately": ["promptly", "forthwith", "without delay", "at once", "expeditiously"],
        "failure": ["inability", "neglect", "omission", "default", "noncompliance"],
        "violation": ["breach", "infringement", "transgression", "contravention", "infraction"],
        "comply": ["adhere", "conform", "abide by", "follow", "observe"],
        "obligation": ["duty", "responsibility", "requirement", "mandate", "commitment"],
        "dispute": ["contest", "challenge", "question", "object to", "take issue with"],
        "remove": ["delete", "expunge", "eliminate", "erase", "strike"],
        "correct": ["rectify", "amend", "fix", "remedy", "revise"],
        "maintain": ["assert", "contend", "hold", "affirm", "state"],
        "demonstrate": ["show", "establish", "prove", "evidence", "illustrate"],
        "pursuant": ["in accordance with", "under", "following", "per", "as required by"],
        "constitute": ["represent", "amount to", "form", "comprise", "make up"],
        "regarding": ["concerning", "with respect to", "pertaining to", "relating to", "as to"],
        "therefore": ["consequently", "thus", "accordingly", "hence", "as a result"],
        "however": ["nevertheless", "nonetheless", "yet", "still", "notwithstanding"],
        "additionally": ["furthermore", "moreover", "also", "in addition", "besides"],
        "specifically": ["particularly", "especially", "notably", "in particular", "expressly"],
        "significant": ["substantial", "considerable", "material", "notable", "meaningful"],
        "ensure": ["guarantee", "assure", "confirm", "make certain", "see to it that"],
        "obtain": ["acquire", "secure", "procure", "get", "receive"],
        "review": ["examine", "assess", "evaluate", "analyze", "inspect"],
        "determine": ["ascertain", "establish", "find", "conclude", "decide"],
    }

    # Civil domain synonyms - maintain accessible register
    CIVIL_SYNONYMS: Dict[str, List[str]] = {
        "request": ["ask", "ask for", "want", "would like", "need"],
        "provide": ["give", "send", "share", "show", "get me"],
        "verify": ["check", "look into", "confirm", "make sure", "double-check"],
        "investigate": ["look into", "check out", "examine", "review", "find out about"],
        "accurate": ["correct", "right", "true", "valid", "proper"],
        "inaccurate": ["wrong", "incorrect", "false", "mistaken", "not right"],
        "information": ["info", "details", "facts", "data", "records"],
        "report": ["record", "file", "statement", "document", "account"],
        "immediately": ["right away", "quickly", "soon", "as soon as possible", "promptly"],
        "failure": ["not being able to", "inability", "problem with", "issue with", "trouble"],
        "problem": ["issue", "concern", "matter", "situation", "difficulty"],
        "fix": ["correct", "resolve", "address", "take care of", "sort out"],
        "help": ["assist", "support", "aid", "give a hand", "be of assistance"],
        "understand": ["see", "get", "realize", "know", "comprehend"],
        "appreciate": ["value", "be grateful for", "thank you for", "am thankful for"],
        "concerned": ["worried", "troubled", "bothered", "anxious", "uneasy"],
        "important": ["significant", "crucial", "vital", "essential", "key"],
        "believe": ["think", "feel", "am confident", "am sure", "trust"],
        "noticed": ["found", "discovered", "saw", "came across", "spotted"],
        "hope": ["trust", "expect", "am hopeful", "look forward to", "anticipate"],
        "situation": ["matter", "issue", "circumstance", "case", "thing"],
        "attention": ["focus", "consideration", "notice", "care", "time"],
        "response": ["reply", "answer", "feedback", "reaction", "word back"],
        "contact": ["reach out to", "get in touch with", "call", "write to", "email"],
    }

    def __init__(self, domain: str, entropy: EntropyController):
        self.domain = domain
        self.entropy = entropy
        self.synonyms = self.LEGAL_SYNONYMS if domain == "legal" else self.CIVIL_SYNONYMS

    def replace_synonyms(self, text: str) -> Tuple[str, int]:
        """
        Replace words with synonyms based on entropy settings.

        Returns:
            Tuple of (modified text, number of replacements)
        """
        replacements = 0
        result = text

        for word, alternatives in self.synonyms.items():
            if not self.entropy.should_mutate("synonym"):
                continue

            # Case-insensitive pattern
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(result))

            for match in matches:
                if self.entropy.should_mutate("synonym"):
                    replacement = self.entropy.select_from_pool(alternatives, 1)[0]
                    # Preserve original case
                    if match.group().isupper():
                        replacement = replacement.upper()
                    elif match.group()[0].isupper():
                        replacement = replacement.capitalize()

                    result = result[:match.start()] + replacement + result[match.end():]
                    replacements += 1
                    break  # Only replace first occurrence per word

        return result, replacements


class ClauseFlipper:
    """Handles clause order transformations."""

    # Patterns for clause flipping (before, connector, after)
    FLIP_PATTERNS = [
        (r'([^,]+),\s*(because|since|as)\s+([^.]+)\.', r'\3, \2 \1.'),
        (r'([^,]+),\s*(although|though|while)\s+([^.]+)\.', r'\3, \2 \1.'),
        (r'(If\s+[^,]+),\s*([^.]+)\.', r'\2 if \1.'),
        (r'([^,]+)\s+(therefore|thus|consequently)\s+([^.]+)\.', r'\3; \2, \1.'),
    ]

    # Compound sentence patterns
    COMPOUND_PATTERNS = [
        (r'([^,]+),\s*and\s+([^.]+)\.', r'\2, and \1.'),
        (r'([^;]+);\s*([^.]+)\.', r'\2; \1.'),
    ]

    def __init__(self, entropy: EntropyController):
        self.entropy = entropy

    def flip_clauses(self, text: str) -> Tuple[str, int]:
        """
        Flip clause order where grammatically appropriate.

        Returns:
            Tuple of (modified text, number of flips)
        """
        flips = 0
        result = text

        # Try subordinate clause flips
        for pattern, replacement in self.FLIP_PATTERNS:
            if self.entropy.should_mutate("clause_flip"):
                new_result, count = re.subn(pattern, replacement, result, count=1)
                if count > 0:
                    result = new_result
                    flips += count

        # Try compound sentence flips
        for pattern, replacement in self.COMPOUND_PATTERNS:
            if self.entropy.should_mutate("clause_flip"):
                new_result, count = re.subn(pattern, replacement, result, count=1)
                if count > 0:
                    result = new_result
                    flips += count

        return result, flips


class PrepositionalReshuffler:
    """Handles prepositional phrase reordering."""

    # Prepositional phrases that can be moved
    MOVABLE_PREPS = [
        r'(in accordance with [^,]+)',
        r'(pursuant to [^,]+)',
        r'(under [^,]+)',
        r'(within \d+ days)',
        r'(at this time)',
        r'(in this matter)',
        r'(on my credit report)',
        r'(in my credit file)',
        r'(to date)',
        r'(as required)',
        r'(without delay)',
        r'(in writing)',
    ]

    def __init__(self, entropy: EntropyController):
        self.entropy = entropy

    def reshuffle(self, text: str) -> Tuple[str, int]:
        """
        Move prepositional phrases to different positions.

        Returns:
            Tuple of (modified text, number of reshuffles)
        """
        reshuffles = 0
        result = text

        for prep_pattern in self.MOVABLE_PREPS:
            if not self.entropy.should_mutate("prepositional"):
                continue

            # Find the prepositional phrase
            match = re.search(prep_pattern, result, re.IGNORECASE)
            if not match:
                continue

            phrase = match.group(1)

            # Determine movement direction
            if self.entropy.should_mutate("prepositional"):
                # Move to beginning of sentence
                sentence_start = result.rfind('.', 0, match.start()) + 1
                if sentence_start > 0:
                    # Remove phrase and its comma
                    temp = result[:match.start()].rstrip(', ') + result[match.end():]
                    # Add to beginning
                    insert_pos = sentence_start
                    while insert_pos < len(temp) and temp[insert_pos] == ' ':
                        insert_pos += 1
                    result = temp[:insert_pos] + phrase.capitalize() + ', ' + temp[insert_pos:].lstrip()
                    reshuffles += 1

        return result, reshuffles


class FillerModifier:
    """Handles filler word addition and removal."""

    # Fillers that can be added (domain-appropriate)
    LEGAL_FILLERS = [
        ("", "hereby "),
        ("", "formally "),
        ("", "expressly "),
        ("I ", "I respectfully "),
        ("must ", "must immediately "),
        ("should ", "should promptly "),
        ("will ", "shall "),
        ("is ", "is clearly "),
        ("are ", "are manifestly "),
    ]

    CIVIL_FILLERS = [
        ("", "really "),
        ("", "actually "),
        ("I ", "I honestly "),
        ("I ", "I truly "),
        ("is ", "is definitely "),
        ("are ", "are certainly "),
        ("hope ", "sincerely hope "),
        ("appreciate ", "really appreciate "),
        ("understand ", "completely understand "),
    ]

    # Fillers that can be removed
    REMOVABLE_FILLERS = [
        "hereby ",
        "formally ",
        "really ",
        "actually ",
        "clearly ",
        "definitely ",
        "certainly ",
        "truly ",
        "honestly ",
        "simply ",
        "just ",
        "basically ",
    ]

    def __init__(self, domain: str, entropy: EntropyController):
        self.domain = domain
        self.entropy = entropy
        self.fillers = self.LEGAL_FILLERS if domain == "legal" else self.CIVIL_FILLERS

    def modify_fillers(self, text: str) -> Tuple[str, int]:
        """
        Add or remove filler words based on entropy.

        Returns:
            Tuple of (modified text, number of modifications)
        """
        modifications = 0
        result = text

        # Add fillers
        for original, with_filler in self.fillers:
            if self.entropy.should_mutate("filler"):
                if original in result:
                    result = result.replace(original, with_filler, 1)
                    modifications += 1

        # Remove fillers
        for filler in self.REMOVABLE_FILLERS:
            if self.entropy.should_mutate("filler"):
                if filler.lower() in result.lower():
                    pattern = re.compile(re.escape(filler), re.IGNORECASE)
                    result = pattern.sub("", result, count=1)
                    modifications += 1

        return result, modifications


class RhetoricalVariator:
    """Handles rhetorical expression variants."""

    # Request variants
    REQUEST_VARIANTS = {
        "legal": [
            ("I request", ["I demand", "I require", "I formally request", "I hereby request"]),
            ("I ask", ["I demand", "I insist", "I require", "I petition"]),
            ("please provide", ["you must provide", "provide immediately", "furnish forthwith"]),
            ("I would like", ["I require", "I demand", "I expect", "I insist upon"]),
        ],
        "civil": [
            ("I request", ["I ask", "I would like", "I'm asking for", "I need"]),
            ("I ask", ["I'm asking", "I'd like to ask", "I'm requesting", "I hope you can"]),
            ("please provide", ["could you provide", "would you please send", "I'd appreciate if you could share"]),
            ("I would like", ["I'm hoping for", "I'd appreciate", "I'm looking for", "I need"]),
        ]
    }

    # Statement variants
    STATEMENT_VARIANTS = {
        "legal": [
            ("This is", ["This constitutes", "This represents", "This amounts to"]),
            ("You must", ["You are obligated to", "You are required to", "It is mandatory that you"]),
            ("I believe", ["I maintain", "I assert", "I contend", "It is my position that"]),
            ("This shows", ["This demonstrates", "This evidences", "This establishes"]),
        ],
        "civil": [
            ("This is", ["This seems to be", "I think this is", "This appears to be"]),
            ("You must", ["You need to", "You should", "I need you to", "Please"]),
            ("I believe", ["I think", "I feel", "It seems to me", "In my view"]),
            ("This shows", ["This tells me", "This indicates", "This suggests"]),
        ]
    }

    def __init__(self, domain: str, entropy: EntropyController):
        self.domain = domain
        self.entropy = entropy
        self.request_variants = self.REQUEST_VARIANTS.get(domain, self.REQUEST_VARIANTS["civil"])
        self.statement_variants = self.STATEMENT_VARIANTS.get(domain, self.STATEMENT_VARIANTS["civil"])

    def apply_variants(self, text: str) -> Tuple[str, int]:
        """
        Apply rhetorical variants to text.

        Returns:
            Tuple of (modified text, number of variants applied)
        """
        variants_applied = 0
        result = text

        # Apply request variants
        for original, alternatives in self.request_variants:
            if original.lower() in result.lower() and self.entropy.should_mutate("rhetorical"):
                replacement = self.entropy.select_from_pool(alternatives, 1)[0]
                pattern = re.compile(re.escape(original), re.IGNORECASE)
                result = pattern.sub(replacement, result, count=1)
                variants_applied += 1

        # Apply statement variants
        for original, alternatives in self.statement_variants:
            if original.lower() in result.lower() and self.entropy.should_mutate("rhetorical"):
                replacement = self.entropy.select_from_pool(alternatives, 1)[0]
                pattern = re.compile(re.escape(original), re.IGNORECASE)
                result = pattern.sub(replacement, result, count=1)
                variants_applied += 1

        return result, variants_applied


class MutationEngine:
    """
    Main mutation engine coordinating all mutation types.
    """

    def __init__(self, domain: str, entropy: EntropyController):
        self.domain = domain
        self.entropy = entropy
        self.synonym_engine = SynonymEngine(domain, entropy)
        self.clause_flipper = ClauseFlipper(entropy)
        self.prep_reshuffler = PrepositionalReshuffler(entropy)
        self.filler_modifier = FillerModifier(domain, entropy)
        self.rhetorical_variator = RhetoricalVariator(domain, entropy)

    def mutate(self, text: str,
               apply_synonyms: bool = True,
               apply_clause_flips: bool = True,
               apply_prep_reshuffling: bool = True,
               apply_filler_mods: bool = True,
               apply_rhetorical: bool = True) -> MutationResult:
        """
        Apply all enabled mutations to text.

        Args:
            text: Input text to mutate
            apply_*: Flags to enable/disable specific mutation types

        Returns:
            MutationResult with modified text and metadata
        """
        result = text
        mutations_applied = []
        total_mutations = 0

        if apply_synonyms:
            result, count = self.synonym_engine.replace_synonyms(result)
            if count > 0:
                mutations_applied.append(f"synonyms:{count}")
                total_mutations += count

        if apply_clause_flips:
            result, count = self.clause_flipper.flip_clauses(result)
            if count > 0:
                mutations_applied.append(f"clause_flips:{count}")
                total_mutations += count

        if apply_prep_reshuffling:
            result, count = self.prep_reshuffler.reshuffle(result)
            if count > 0:
                mutations_applied.append(f"prep_reshuffles:{count}")
                total_mutations += count

        if apply_filler_mods:
            result, count = self.filler_modifier.modify_fillers(result)
            if count > 0:
                mutations_applied.append(f"filler_mods:{count}")
                total_mutations += count

        if apply_rhetorical:
            result, count = self.rhetorical_variator.apply_variants(result)
            if count > 0:
                mutations_applied.append(f"rhetorical:{count}")
                total_mutations += count

        return MutationResult(
            text=result,
            mutations_applied=mutations_applied,
            mutation_count=total_mutations
        )

    def mutate_paragraph(self, paragraph: str) -> MutationResult:
        """
        Mutate a full paragraph, applying mutations sentence by sentence.
        """
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        mutated_sentences = []
        all_mutations = []
        total_count = 0

        for sentence in sentences:
            result = self.mutate(sentence)
            mutated_sentences.append(result.text)
            all_mutations.extend(result.mutations_applied)
            total_count += result.mutation_count

        return MutationResult(
            text=' '.join(mutated_sentences),
            mutations_applied=all_mutations,
            mutation_count=total_count
        )

    def mutate_sections(self, sections: List[str]) -> List[MutationResult]:
        """
        Mutate multiple sections independently.
        """
        return [self.mutate_paragraph(section) for section in sections]


def create_mutation_engine(domain: str, entropy: EntropyController) -> MutationEngine:
    """
    Factory function to create a mutation engine.

    Args:
        domain: "legal" or "civil"
        entropy: EntropyController instance

    Returns:
        Configured MutationEngine
    """
    return MutationEngine(domain, entropy)
