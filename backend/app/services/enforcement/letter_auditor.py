"""
Credit Engine 2.0 - Letter Auditor
Regulatory compliance auditor for FCRA enforcement letters.

ROLE: Audit and harden draft enforcement letters.
- Does NOT provide legal advice
- Does NOT add new facts
- Does NOT invent violations
- Sole function: Harden the provided enforcement artifact
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AuditResult:
    """Result of letter audit."""
    audited_letter: str
    change_log: List[str]
    issues_found: int
    issues_corrected: int
    audit_score: int


class LetterAuditor:
    """
    Audits and hardens FCRA enforcement letters according to regulatory standards.
    """

    # Canonical statute format patterns
    STATUTE_CORRECTIONS = {
        # FCRA variations to canonical form
        r'15\s*USC\s*§?\s*1681i\s*\(\s*a\s*\)\s*\(\s*1\s*\)\s*\(\s*A\s*\)': '15 U.S.C. § 1681i(a)(1)(A)',
        r'15\s*USC\s*§?\s*1681i\s*\(\s*a\s*\)\s*\(\s*5\s*\)\s*\(\s*B\s*\)': '15 U.S.C. § 1681i(a)(5)(B)',
        r'15\s*USC\s*§?\s*1681i\s*\(\s*a\s*\)\s*\(\s*3\s*\)': '15 U.S.C. § 1681i(a)(3)',
        r'15\s*USC\s*§?\s*1681i\s*\(\s*a\s*\)\s*\(\s*3\s*\)\s*\(\s*A\s*\)': '15 U.S.C. § 1681i(a)(3)(A)',
        r'15\s*USC\s*§?\s*1681i\s*\(\s*a\s*\)\s*\(\s*3\s*\)\s*\(\s*B\s*\)': '15 U.S.C. § 1681i(a)(3)(B)',
        r'15\s*USC\s*§?\s*1681n': '15 U.S.C. § 1681n',
        r'15\s*USC\s*§?\s*1681o': '15 U.S.C. § 1681o',
        r'15\s*USC\s*§?\s*1681c\s*\(\s*a\s*\)': '15 U.S.C. § 1681c(a)',
        r'15\s*USC\s*§?\s*1681s-2\s*\(\s*b\s*\)\s*\(\s*1\s*\)': '15 U.S.C. § 1681s-2(b)(1)',
        r'15\s*USC\s*§?\s*1681s-2\s*\(\s*b\s*\)\s*\(\s*1\s*\)\s*\(\s*A\s*\)': '15 U.S.C. § 1681s-2(b)(1)(A)',
        # FDCPA variations
        r'15\s*USC\s*§?\s*1692g\s*\(\s*b\s*\)': '15 U.S.C. § 1692g(b)',
        r'15\s*USC\s*§?\s*1692e': '15 U.S.C. § 1692e',
        r'15\s*USC\s*§?\s*1692f': '15 U.S.C. § 1692f',
        r'15\s*USC\s*§?\s*1692k': '15 U.S.C. § 1692k',
        # Generic USC pattern cleanup
        r'(\d+)\s*U\.?S\.?C\.?\s*§?\s*(\d+)': r'\1 U.S.C. § \2',
    }

    # Advisory/soft language to replace with enforcement language
    TONE_CORRECTIONS = [
        # Request-style to demand-style
        (r'\bwe\s+(?:would\s+)?(?:kindly\s+)?request\s+that\s+you\b', 'you are hereby required to'),
        (r'\bplease\s+(?:consider|review|look\s+into)\b', 'you must'),
        (r'\bwe\s+(?:would\s+)?appreciate\s+(?:it\s+)?if\s+you\s+(?:could|would)\b', 'you are required to'),
        (r'\bwe\s+ask\s+that\s+you\b', 'you must'),
        (r'\bwe\s+hope\s+(?:that\s+)?you\s+(?:will|can)\b', 'you are required to'),
        (r'\bif\s+you\s+could\s+(?:please\s+)?\b', ''),
        (r'\bwe\s+encourage\s+you\s+to\b', 'you must'),
        (r'\bit\s+would\s+be\s+helpful\s+if\b', 'you are required to'),
        # Softening language removal
        (r'\bperhaps\b', ''),
        (r'\bpossibly\b', ''),
        (r'\bmay\s+(?:wish|want)\s+to\b', 'must'),
        (r'\bmight\s+consider\b', 'must'),
        (r'\bshould\s+consider\b', 'must'),
        # Politeness markers
        (r'\bthank\s+you\s+(?:for\s+your\s+)?(?:attention|cooperation|time)\b', ''),
        (r'\bwe\s+look\s+forward\s+to\s+(?:hearing\s+from\s+you|your\s+response)\b', ''),
    ]

    # Educational/explanatory patterns to remove
    EDUCATIONAL_PATTERNS = [
        r'[Uu]nder\s+the\s+(?:Fair\s+Credit\s+Reporting\s+Act|FCRA),?\s+(?:you|credit\s+reporting\s+agencies?)\s+(?:are|is)\s+required\s+to[^.]+\.',
        r'[Tt]he\s+(?:FCRA|Fair\s+Credit\s+Reporting\s+Act)\s+(?:requires|mandates|provides)\s+that[^.]+\.',
        r'[Aa]s\s+you\s+(?:may\s+)?know,?\s+[^.]+\.',
        r'[Ff]or\s+your\s+(?:information|reference),?\s+[^.]+\.',
        r'[Ii]t\s+is\s+important\s+to\s+(?:note|understand)\s+that[^.]+\.',
    ]

    # Speculative language patterns
    SPECULATIVE_PATTERNS = [
        r'\b(?:it\s+appears\s+that|apparently|seemingly|presumably)\b[^.]*\.',
        r'\bwe\s+(?:believe|suspect|think)\s+that\b[^.]*\.',
        r'\b(?:may\s+have|might\s+have|could\s+have)\s+(?:been|caused)\b',
        r'\bthis\s+(?:suggests|indicates|implies)\s+that\b',
    ]

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.changes_made: List[str] = []
        self.issues_found = 0
        self.issues_corrected = 0

    def audit(self, letter_content: str) -> AuditResult:
        """
        Audit and harden an enforcement letter.

        Args:
            letter_content: The draft letter to audit

        Returns:
            AuditResult with corrected letter and change log
        """
        self.changes_made = []
        self.issues_found = 0
        self.issues_corrected = 0

        audited = letter_content

        # 1. Statutory Precision
        audited = self._correct_statute_citations(audited)

        # 2. Enforcement Tone
        audited = self._correct_tone(audited)

        # 3. Remove Educational Language
        audited = self._remove_educational_language(audited)

        # 4. Remove Speculative Language
        audited = self._remove_speculative_language(audited)

        # 5. Structural Cleanup
        audited = self._cleanup_structure(audited)

        # 6. Verify Liability Preservation
        audited = self._verify_liability_preservation(audited)

        # Calculate audit score
        audit_score = self._calculate_audit_score()

        # Consolidate change log to max 5 items
        change_log = self._consolidate_change_log()

        return AuditResult(
            audited_letter=audited,
            change_log=change_log,
            issues_found=self.issues_found,
            issues_corrected=self.issues_corrected,
            audit_score=audit_score
        )

    def _correct_statute_citations(self, text: str) -> str:
        """Correct statute citations to canonical USC format."""
        corrections_made = 0

        for pattern, replacement in self.STATUTE_CORRECTIONS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                self.issues_found += len(matches)
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                corrections_made += len(matches)
                self.issues_corrected += len(matches)

        if corrections_made > 0:
            self.changes_made.append(
                f"Corrected {corrections_made} statute citation(s) to canonical USC format"
            )

        return text

    def _correct_tone(self, text: str) -> str:
        """Replace advisory language with enforcement language."""
        corrections_made = 0

        for pattern, replacement in self.TONE_CORRECTIONS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                self.issues_found += len(matches)
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                corrections_made += len(matches)
                self.issues_corrected += len(matches)

        if corrections_made > 0:
            self.changes_made.append(
                f"Replaced {corrections_made} advisory phrase(s) with regulatory demands"
            )

        return text

    def _remove_educational_language(self, text: str) -> str:
        """Remove explanatory/educational language."""
        removals_made = 0

        for pattern in self.EDUCATIONAL_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                self.issues_found += len(matches)
                text = re.sub(pattern, '', text)
                removals_made += len(matches)
                self.issues_corrected += len(matches)

        if removals_made > 0:
            self.changes_made.append(
                f"Removed {removals_made} educational/explanatory sentence(s)"
            )

        return text

    def _remove_speculative_language(self, text: str) -> str:
        """Remove speculative assertions."""
        removals_made = 0

        for pattern in self.SPECULATIVE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                self.issues_found += len(matches)
                if self.strict_mode:
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE)
                    removals_made += len(matches)
                    self.issues_corrected += len(matches)

        if removals_made > 0:
            self.changes_made.append(
                f"Removed {removals_made} speculative assertion(s)"
            )

        return text

    def _cleanup_structure(self, text: str) -> str:
        """Clean up structural issues."""
        changes = 0

        # Remove multiple consecutive blank lines
        original = text
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        if text != original:
            changes += 1

        # Remove trailing whitespace on lines
        original = text
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        if text != original:
            changes += 1

        # Ensure proper spacing after periods
        original = text
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        if text != original:
            changes += 1

        if changes > 0:
            self.changes_made.append("Cleaned structural formatting")
            self.issues_found += changes
            self.issues_corrected += changes

        return text

    def _verify_liability_preservation(self, text: str) -> str:
        """Verify willful/negligent noncompliance exposure is preserved."""
        # Check for §1681n (willful) or §1681o (negligent) references
        has_willful_ref = bool(re.search(r'1681n|willful', text, re.IGNORECASE))
        has_negligent_ref = bool(re.search(r'1681o|negligent', text, re.IGNORECASE))

        if not has_willful_ref and not has_negligent_ref:
            # Note this but don't auto-add - auditor doesn't add facts
            self.issues_found += 1
            self.changes_made.append(
                "Note: Letter lacks explicit §1681n/§1681o liability preservation language"
            )

        return text

    def _calculate_audit_score(self) -> int:
        """Calculate audit score based on issues found vs corrected."""
        if self.issues_found == 0:
            return 100

        correction_rate = self.issues_corrected / self.issues_found
        base_score = int(correction_rate * 100)

        # Bonus for clean letters
        if self.issues_found < 3:
            base_score = min(100, base_score + 10)

        return min(100, max(0, base_score))

    def _consolidate_change_log(self) -> List[str]:
        """Consolidate change log to maximum 5 items."""
        if len(self.changes_made) <= 5:
            return self.changes_made

        # Group similar changes
        consolidated = []
        statute_changes = [c for c in self.changes_made if 'statute' in c.lower() or 'citation' in c.lower()]
        tone_changes = [c for c in self.changes_made if 'tone' in c.lower() or 'advisory' in c.lower() or 'demand' in c.lower()]
        removal_changes = [c for c in self.changes_made if 'removed' in c.lower()]
        other_changes = [c for c in self.changes_made if c not in statute_changes + tone_changes + removal_changes]

        if statute_changes:
            consolidated.append(statute_changes[0])
        if tone_changes:
            consolidated.append(tone_changes[0])
        if removal_changes:
            total_removals = sum(int(re.search(r'\d+', c).group()) for c in removal_changes if re.search(r'\d+', c))
            consolidated.append(f"Removed {total_removals} non-compliant phrase(s)")
        consolidated.extend(other_changes[:2])

        return consolidated[:5]


def audit_enforcement_letter(letter_content: str, strict_mode: bool = True) -> Dict:
    """
    Convenience function to audit an enforcement letter.

    Args:
        letter_content: The draft letter to audit
        strict_mode: If True, removes speculative language; if False, only flags it

    Returns:
        Dict with audited_letter, change_log, issues_found, issues_corrected, audit_score
    """
    auditor = LetterAuditor(strict_mode=strict_mode)
    result = auditor.audit(letter_content)

    return {
        "audited_letter": result.audited_letter,
        "change_log": result.change_log,
        "issues_found": result.issues_found,
        "issues_corrected": result.issues_corrected,
        "audit_score": result.audit_score
    }
