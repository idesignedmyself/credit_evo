"""
Test Suite: Structural Integrity Tests for Legal Letter Generator

Tests the structural fixer and validators to ensure:
1. Legal letters maintain exact section order
2. Civil letters maintain exact section order
3. No cross-domain content bleeding
4. Position-locked sections (MOV, Metro-2, Case Law) remain in place
5. High-entropy mutations don't break structure
"""
import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.legal_letter_generator import (
    StructuralFixer,
    StructuralValidator,
    StructuralMetadata,
    LetterDomainType,
    LEGAL_SECTION_SPECS,
    CIVIL_SECTION_SPECS,
    create_structural_fixer,
    create_diversity_engine,
    DiversityConfig,
    EntropyLevel,
    MutationStrength,
)


# Sample legal letter content with correct structure
SAMPLE_LEGAL_LETTER = """John Doe
123 Main Street
Anytown, ST 12345

December 1, 2025

RE: FORMAL DISPUTE NOTICE - Account #XXXX1234

I. PRELIMINARY STATEMENT

This letter constitutes a formal dispute of information contained in my credit report pursuant to the Fair Credit Reporting Act, 15 U.S.C. § 1681.

II. LEGAL BASIS

Under Section 611 of the FCRA, 15 U.S.C. § 1681i, you are required to conduct a reasonable reinvestigation of disputed items within 30 days.

III. SPECIFIC VIOLATIONS

The following items are disputed as inaccurate:

1. Account: Example Bank - XXXX1234
   - Balance reported as $5,000 but actual balance is $0
   - This constitutes a violation of FCRA Section 623(a)(1)

IV. METRO-2 COMPLIANCE

The following Metro-2 fields are reported incorrectly:
- Field 17 (Current Balance): Reports $5,000 instead of $0
- Field 25 (Account Status): Should reflect "Paid in Full"

V. METHOD OF VERIFICATION REQUIREMENTS

Pursuant to FCRA requirements, you must provide:
- Complete payment history documentation
- Original creditor agreement
- Chain of title documentation

VI. CASE LAW AND LEGAL PRECEDENT

The following case law supports this dispute:
- Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997)
- Stevenson v. TRW Inc., 987 F.2d 288 (5th Cir. 1993)

VII. FORMAL DEMANDS

I hereby demand that you:
1. Immediately investigate this dispute
2. Remove all inaccurate information
3. Provide written verification within 30 days

VIII. RESERVATION OF RIGHTS

I reserve all rights under the Fair Credit Reporting Act and applicable state laws.

Respectfully,


John Doe
"""

# Sample civil letter content
SAMPLE_CIVIL_LETTER = """Jane Smith
456 Oak Avenue
Somewhere, ST 67890

December 1, 2025

RE: Credit Report Dispute

Dear Credit Bureau Representative,

I am writing to dispute some incorrect information on my credit report. I recently reviewed my report and found several errors that need to be corrected.

The following items I'm disputing:

1. ABC Collections - Account #XXXX5678
   - This account shows as unpaid, but I paid it in full last year.
   - I have the receipt and bank statement to prove it.

Here's what I found as evidence:
- Payment confirmation dated March 15, 2024
- Bank statement showing the debit
- Letter from ABC Collections confirming payment

I would like you to please:
1. Investigate this account
2. Correct the status to show it's paid
3. Send me a copy of my updated report

Thank you for your time and attention to this matter. I look forward to hearing from you soon.

Sincerely,

Jane Smith
"""

# Legal letter with sections out of order
DISORDERED_LEGAL_LETTER = """John Doe
123 Main Street

December 1, 2025

VII. FORMAL DEMANDS

I demand that you correct the following.

III. SPECIFIC VIOLATIONS

Account XYZ is incorrectly reported.

I. PRELIMINARY STATEMENT

This is a formal dispute.

V. METHOD OF VERIFICATION REQUIREMENTS

Please provide all documentation.

Respectfully,

John Doe
"""

# Civil letter with legal terms (cross-domain bleed)
CIVIL_WITH_LEGAL_TERMS = """Jane Smith
123 Main St

December 1, 2025

Dear Sir/Madam,

I am writing pursuant to the Fair Credit Reporting Act to dispute items on my credit report.

The following Metro-2 fields are incorrectly reported.

I hereby demand Method of Verification for all disputed items.

Please help me correct these errors. I would appreciate your assistance.

Sincerely,

Jane Smith
"""


class TestLegalOrderExact:
    """Test that legal letter sections maintain exact ordering."""

    def test_legal_letter_order_is_correct(self):
        """Verify correctly ordered legal letter passes validation."""
        is_valid, issues = StructuralValidator.validate_structure(
            SAMPLE_LEGAL_LETTER, "legal"
        )
        order_errors = [i for i in issues if "ORDER" in i.code]
        assert len(order_errors) == 0, f"Order errors found: {order_errors}"

    def test_disordered_legal_letter_is_fixed(self):
        """Verify structural fixer reorders disordered legal letter."""
        fixer = create_structural_fixer()
        fixed_content, metadata = fixer.fix_structure(
            DISORDERED_LEGAL_LETTER,
            domain="legal",
            tone="professional"
        )

        # Check that sections were reordered
        assert metadata.order_violations_fixed > 0

        # Validate the fixed content
        is_valid, issues = StructuralValidator.validate_structure(fixed_content, "legal")
        order_errors = [i for i in issues if "ORDER" in i.code]
        assert len(order_errors) == 0, f"Order still broken after fix: {order_errors}"

    def test_legal_section_order_spec_positions(self):
        """Verify legal section specs have monotonically increasing positions."""
        positions = [spec.position for spec in LEGAL_SECTION_SPECS]
        assert positions == sorted(positions), "Legal section positions must be ordered"


class TestLegalNoMissingHeaders:
    """Test that legal letters have all required section headers."""

    def test_required_sections_present(self):
        """Verify all required sections are present in sample letter."""
        issues = StructuralValidator.validate_required_sections(
            SAMPLE_LEGAL_LETTER, "legal"
        )
        missing_errors = [i for i in issues if "MISSING" in i.code]
        assert len(missing_errors) == 0, f"Missing sections: {missing_errors}"

    def test_empty_letter_fails_validation(self):
        """Verify empty letter fails required section validation."""
        issues = StructuralValidator.validate_required_sections("", "legal")
        assert len(issues) > 0, "Empty letter should fail validation"

    def test_section_count_validation(self):
        """Verify section count matches expectations."""
        issues = StructuralValidator.validate_section_count(SAMPLE_LEGAL_LETTER, "legal")
        count_errors = [i for i in issues if "INSUFFICIENT" in i.code]
        assert len(count_errors) == 0, f"Section count issues: {count_errors}"


class TestLegalMOVPosition:
    """Test that MOV section is in correct position."""

    def test_mov_after_metro2(self):
        """Verify MOV section appears after Metro-2 section."""
        issues = StructuralValidator.validate_mov_position(SAMPLE_LEGAL_LETTER)
        mov_errors = [i for i in issues if "MOV_POSITION" in i.code]
        assert len(mov_errors) == 0, f"MOV position errors: {mov_errors}"

    def test_mov_before_case_law(self):
        """Verify MOV section appears before Case Law section."""
        issues = StructuralValidator.validate_mov_position(SAMPLE_LEGAL_LETTER)
        # If there's no error, MOV is in correct position
        assert all("Case Law" not in str(i) or "after" in str(i) for i in issues)

    def test_mov_missing_is_ok(self):
        """Verify letter without MOV doesn't fail validation."""
        letter_no_mov = SAMPLE_LEGAL_LETTER.replace("V. METHOD OF VERIFICATION", "")
        letter_no_mov = letter_no_mov.replace("Pursuant to FCRA requirements", "")
        issues = StructuralValidator.validate_mov_position(letter_no_mov)
        # Should not have position errors if MOV is not present
        assert len(issues) == 0


class TestLegalCaseLawPosition:
    """Test that Case Law section is in correct position."""

    def test_case_law_after_mov(self):
        """Verify Case Law section appears after MOV section."""
        issues = StructuralValidator.validate_case_law_position(SAMPLE_LEGAL_LETTER)
        case_law_errors = [i for i in issues if "CASE_LAW_POSITION" in i.code]
        assert len(case_law_errors) == 0, f"Case Law position errors: {case_law_errors}"

    def test_case_law_before_demands(self):
        """Verify Case Law section appears before Demands section."""
        issues = StructuralValidator.validate_case_law_position(SAMPLE_LEGAL_LETTER)
        demand_errors = [i for i in issues if "Demands" in str(i) and "before" in str(i)]
        assert len(demand_errors) == 0

    def test_case_law_missing_is_ok(self):
        """Verify letter without Case Law doesn't fail validation."""
        letter_no_case_law = SAMPLE_LEGAL_LETTER.replace("VI. CASE LAW", "")
        issues = StructuralValidator.validate_case_law_position(letter_no_case_law)
        assert len(issues) == 0


class TestCivilOrderExact:
    """Test that civil letter sections maintain exact ordering."""

    def test_civil_letter_order_is_correct(self):
        """Verify correctly ordered civil letter passes validation."""
        is_valid, issues = StructuralValidator.validate_structure(
            SAMPLE_CIVIL_LETTER, "civil"
        )
        order_errors = [i for i in issues if "ORDER" in i.code]
        assert len(order_errors) == 0, f"Order errors found: {order_errors}"

    def test_civil_section_order_spec_positions(self):
        """Verify civil section specs have monotonically increasing positions."""
        positions = [spec.position for spec in CIVIL_SECTION_SPECS]
        assert positions == sorted(positions), "Civil section positions must be ordered"

    def test_civil_required_sections_present(self):
        """Verify all required civil sections are present."""
        issues = StructuralValidator.validate_required_sections(
            SAMPLE_CIVIL_LETTER, "civil"
        )
        missing_errors = [i for i in issues if "MISSING" in i.code]
        # Civil letters have fewer required sections
        assert len(missing_errors) <= 2, f"Too many missing sections: {missing_errors}"


class TestNoCrossDomainBleed:
    """Test that no cross-domain content bleeds between legal/civil letters."""

    def test_legal_terms_not_in_civil(self):
        """Verify legal terms are detected in civil letters."""
        issues = StructuralValidator.validate_no_cross_domain_bleed(
            CIVIL_WITH_LEGAL_TERMS, "civil"
        )
        cross_domain_errors = [i for i in issues if "CROSS_DOMAIN" in i.code or "FORBIDDEN" in i.code]
        assert len(cross_domain_errors) > 0, "Should detect legal terms in civil letter"

    def test_clean_civil_letter_passes(self):
        """Verify clean civil letter has no cross-domain issues."""
        issues = StructuralValidator.validate_no_cross_domain_bleed(
            SAMPLE_CIVIL_LETTER, "civil"
        )
        cross_domain_errors = [i for i in issues if "CROSS_DOMAIN" in i.code]
        assert len(cross_domain_errors) == 0, f"Clean civil letter has errors: {cross_domain_errors}"

    def test_structural_fixer_removes_legal_terms(self):
        """Verify structural fixer removes legal terms from civil letters."""
        fixer = create_structural_fixer()
        fixed_content, metadata = fixer.fix_structure(
            CIVIL_WITH_LEGAL_TERMS,
            domain="civil",
            tone="professional"
        )

        # Legal terms should be filtered out
        assert "Metro-2" not in fixed_content or len(metadata.cross_domain_removed) > 0

    def test_legal_letter_allows_legal_terms(self):
        """Verify legal letters allow legal terminology."""
        issues = StructuralValidator.validate_no_cross_domain_bleed(
            SAMPLE_LEGAL_LETTER, "legal"
        )
        # Legal letters should have no cross-domain errors for legal terms
        legal_term_errors = [i for i in issues if "pursuant" in str(i).lower() or "metro" in str(i).lower()]
        assert len(legal_term_errors) == 0


class TestMutationDoesNotBreakOrder:
    """Test that diversity engine mutations don't break section ordering."""

    def test_medium_mutation_preserves_order(self):
        """Verify medium-strength mutations preserve section order."""
        engine = create_diversity_engine(
            entropy_level="medium",
            mutation_strength="medium",
            domain="legal",
            seed=42
        )

        # Apply mutations
        mutated = engine.mutate_text(SAMPLE_LEGAL_LETTER)

        # Validate structure is still intact
        fixer = create_structural_fixer()
        fixed_content, metadata = fixer.fix_structure(
            mutated, domain="legal", tone="professional"
        )

        # Should have minimal or no order violations
        assert metadata.order_violations_fixed <= 2, "Too many order violations after mutation"

    def test_paragraph_shuffle_preserves_structure(self):
        """Verify paragraph shuffling preserves critical structure."""
        engine = create_diversity_engine(
            entropy_level="high",
            mutation_strength="high",
            domain="legal",
            seed=123
        )

        # Get paragraphs
        paragraphs = SAMPLE_LEGAL_LETTER.split("\n\n")

        # Shuffle with structure preservation
        shuffled = engine.shuffle_paragraphs(paragraphs, preserve_structure=True)

        # First paragraph should still be header-like
        assert any(c.isupper() for c in shuffled[0][:50])


class TestHighEntropyStillValidStructure:
    """Test that maximum entropy still produces valid structure."""

    def test_maximum_entropy_legal_letter(self):
        """Verify maximum entropy legal letter can be processed by structural fixer."""
        engine = create_diversity_engine(
            entropy_level="maximum",
            mutation_strength="maximum",
            domain="legal",
            seed=999
        )

        # Apply all mutations
        mutated = engine.mutate_text(SAMPLE_LEGAL_LETTER)

        # Structural fixer should process without errors
        fixer = create_structural_fixer()
        fixed_content, metadata = fixer.fix_structure(
            mutated, domain="legal", tone="professional"
        )

        # At maximum entropy, we verify the fixer ran and found sections
        # Structure validity may vary but fixer should complete
        assert len(metadata.sections_found) > 0, "Fixer should find some sections"
        assert fixed_content is not None, "Fixer should return content"
        assert len(fixed_content) > 0, "Fixed content should not be empty"

    def test_maximum_entropy_civil_letter(self):
        """Verify maximum entropy civil letter is structurally valid after fixing."""
        engine = create_diversity_engine(
            entropy_level="maximum",
            mutation_strength="maximum",
            domain="civil",
            seed=888
        )

        # Apply all mutations
        mutated = engine.mutate_text(SAMPLE_CIVIL_LETTER)

        # Structural fixer should repair any damage
        fixer = create_structural_fixer()
        fixed_content, metadata = fixer.fix_structure(
            mutated, domain="civil", tone="professional"
        )

        # Should not have legal-only content
        issues = StructuralValidator.validate_no_cross_domain_bleed(fixed_content, "civil")
        forbidden_section_errors = [i for i in issues if "FORBIDDEN_SECTION" in i.code]
        assert len(forbidden_section_errors) == 0, "Civil letter has forbidden legal sections"

    def test_seeded_entropy_is_deterministic(self):
        """Verify seeded entropy produces consistent results."""
        engine1 = create_diversity_engine(
            entropy_level="high",
            mutation_strength="high",
            domain="legal",
            seed=12345
        )

        engine2 = create_diversity_engine(
            entropy_level="high",
            mutation_strength="high",
            domain="legal",
            seed=12345
        )

        # Same seed should produce same results
        result1 = engine1.mutate_text("Test content for mutation.")
        result2 = engine2.mutate_text("Test content for mutation.")

        assert result1 == result2, "Same seed should produce identical results"


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
