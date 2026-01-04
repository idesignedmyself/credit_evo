"""
Hard Delete Service

Canonical, transactional deletion of letters and disputes with full dependency teardown.
No soft-delete, no status flags, no archival.
"""
from sqlalchemy.orm import Session


class HardDeleteService:
    """
    Centralized hard delete service.
    Single source of truth for dependency discovery and ordered deletion.
    """

    def __init__(self, db: Session):
        self.db = db

    def delete_letter(self, letter_id: str, user_id: str) -> dict:
        """
        Hard delete a letter and all dependent records.

        Deletion order:
        1. Find disputes referencing this letter
        2. For each dispute: delete all child records
        3. Delete disputes
        4. Delete execution_events by letter_id
        5. Delete the letter

        Returns cascade counts for confirmation.
        """
        from ..models.db_models import (
            LetterDB, DisputeDB, ExecutionEventDB,
            DisputeResponseDB, Tier2ResponseDB, ReinsertionWatchDB,
            EscalationLogDB, PaperTrailDB, SchedulerTaskDB
        )

        letter = self.db.query(LetterDB).filter(
            LetterDB.id == letter_id,
            LetterDB.user_id == user_id
        ).first()

        if not letter:
            return None

        cascade = {
            "disputes": 0,
            "execution_events": 0,
            "dispute_responses": 0,
            "tier2_responses": 0,
            "reinsertion_watches": 0,
            "escalation_logs": 0,
            "paper_trail": 0,
            "scheduler_tasks": 0,
            "related_letters": 0,
        }

        # Step 1: Find disputes referencing this letter
        dispute_ids = [
            d.id for d in
            self.db.query(DisputeDB.id).filter(DisputeDB.letter_id == letter_id).all()
        ]

        if dispute_ids:
            # Step 2: Delete all child records of disputes
            cascade["execution_events"] += self.db.query(ExecutionEventDB).filter(
                ExecutionEventDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            cascade["dispute_responses"] = self.db.query(DisputeResponseDB).filter(
                DisputeResponseDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            cascade["tier2_responses"] = self.db.query(Tier2ResponseDB).filter(
                Tier2ResponseDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            cascade["reinsertion_watches"] = self.db.query(ReinsertionWatchDB).filter(
                ReinsertionWatchDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            cascade["escalation_logs"] = self.db.query(EscalationLogDB).filter(
                EscalationLogDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            cascade["paper_trail"] = self.db.query(PaperTrailDB).filter(
                PaperTrailDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            cascade["scheduler_tasks"] = self.db.query(SchedulerTaskDB).filter(
                SchedulerTaskDB.dispute_id.in_(dispute_ids)
            ).delete(synchronize_session=False)

            # Delete related letters (response letters for these disputes)
            cascade["related_letters"] = self.db.query(LetterDB).filter(
                LetterDB.dispute_id.in_(dispute_ids),
                LetterDB.id != letter_id
            ).delete(synchronize_session=False)

            # Step 3: Delete disputes
            cascade["disputes"] = self.db.query(DisputeDB).filter(
                DisputeDB.id.in_(dispute_ids)
            ).delete(synchronize_session=False)

        # Step 4: Delete execution_events by letter_id
        cascade["execution_events"] += self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.letter_id == letter_id
        ).delete(synchronize_session=False)

        # Step 5: Delete the letter
        self.db.delete(letter)
        self.db.commit()

        return cascade

    def delete_dispute(self, dispute_id: str, user_id: str) -> dict:
        """
        Hard delete a dispute and all dependent records.

        Deletion order:
        1. Delete all child records (execution_events, responses, watches, etc.)
        2. Delete related letters (response letters)
        3. Delete the dispute

        Returns cascade counts for confirmation.
        """
        from ..models.db_models import (
            LetterDB, DisputeDB, ExecutionEventDB,
            DisputeResponseDB, Tier2ResponseDB, ReinsertionWatchDB,
            EscalationLogDB, PaperTrailDB, SchedulerTaskDB
        )

        dispute = self.db.query(DisputeDB).filter(
            DisputeDB.id == dispute_id,
            DisputeDB.user_id == user_id
        ).first()

        if not dispute:
            return None

        cascade = {
            "execution_events": 0,
            "dispute_responses": 0,
            "tier2_responses": 0,
            "reinsertion_watches": 0,
            "escalation_logs": 0,
            "paper_trail": 0,
            "scheduler_tasks": 0,
            "related_letters": 0,
        }

        # Step 1: Delete all child records
        cascade["execution_events"] = self.db.query(ExecutionEventDB).filter(
            ExecutionEventDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        cascade["dispute_responses"] = self.db.query(DisputeResponseDB).filter(
            DisputeResponseDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        cascade["tier2_responses"] = self.db.query(Tier2ResponseDB).filter(
            Tier2ResponseDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        cascade["reinsertion_watches"] = self.db.query(ReinsertionWatchDB).filter(
            ReinsertionWatchDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        cascade["escalation_logs"] = self.db.query(EscalationLogDB).filter(
            EscalationLogDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        cascade["paper_trail"] = self.db.query(PaperTrailDB).filter(
            PaperTrailDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        cascade["scheduler_tasks"] = self.db.query(SchedulerTaskDB).filter(
            SchedulerTaskDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        # Step 2: Delete related letters (response letters for this dispute)
        cascade["related_letters"] = self.db.query(LetterDB).filter(
            LetterDB.dispute_id == dispute_id
        ).delete(synchronize_session=False)

        # Step 3: Delete the dispute
        self.db.delete(dispute)
        self.db.commit()

        return cascade
