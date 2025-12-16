"""
Reinsertion Detector

AUTHORITY: SYSTEM
This module creates violations AUTOMATICALLY without user confirmation.
User's only role is uploading reports - detection and escalation are system-authoritative.

Key behaviors:
- Scans for previously deleted items during report ingestion
- Creates FCRA § 611(a)(5)(B) violation if reinsertion detected without notice
- Creates FCRA § 623(a)(6) violation against furnisher if applicable
- Auto-escalates to REGULATORY_ESCALATION without user confirmation
- Treats reinsertion without notice as willful noncompliance (§616 exposure)

The 90-day monitoring window starts when an item is DELETED.
If the item reappears without 5-day advance notice, it's an automatic violation.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from ...models.db_models import (
    DisputeDB, ReinsertionWatchDB, PaperTrailDB, EscalationLogDB,
    EscalationState, ActorType, ReinsertionWatchStatus
)


# =============================================================================
# REINSERTION DETECTOR
# =============================================================================

class ReinsertionDetector:
    """
    Detects reinsertion of previously deleted items.

    This is a SYSTEM-DETECTED violation, not user-reported.
    Operates automatically during report ingestion.

    FCRA § 611(a)(5)(B) Requirements:
    - CRA must provide 5-day advance notice before reinsertion
    - Must certify information is complete and accurate
    - Failure to comply = automatic violation
    """

    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db = db_session

    def get_active_watches(self, user_id: str = None) -> List[ReinsertionWatchDB]:
        """Get all active reinsertion watches."""
        query = self.db.query(ReinsertionWatchDB).filter(
            ReinsertionWatchDB.status == ReinsertionWatchStatus.ACTIVE,
            ReinsertionWatchDB.monitoring_end >= date.today(),
        )

        if user_id:
            query = query.join(DisputeDB).filter(DisputeDB.user_id == user_id)

        return query.all()

    def generate_account_fingerprint(
        self,
        creditor_name: str,
        account_number_partial: str = None,
        bureau: str = None,
    ) -> str:
        """
        Generate a fingerprint for account matching.

        Used to identify if a deleted account has reappeared.
        """
        components = [creditor_name.upper().strip()]

        if account_number_partial:
            components.append(account_number_partial)

        if bureau:
            components.append(bureau.upper())

        return "_".join(components)

    def check_for_reinsertion(
        self,
        watch: ReinsertionWatchDB,
        current_accounts: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a watched account has been reinserted.

        Args:
            watch: The reinsertion watch record
            current_accounts: List of accounts from new report

        Returns:
            (is_reinserted, match_details)
        """
        watch_fingerprint = watch.account_fingerprint.upper()

        for account in current_accounts:
            # Generate fingerprint for current account
            current_fingerprint = self.generate_account_fingerprint(
                creditor_name=account.get("creditor_name", ""),
                account_number_partial=account.get("account_number_partial"),
                bureau=account.get("bureau"),
            )

            # Check for match
            if watch_fingerprint in current_fingerprint or current_fingerprint in watch_fingerprint:
                return True, {
                    "watch_id": watch.id,
                    "watch_fingerprint": watch_fingerprint,
                    "matched_account": account,
                    "deletion_date": watch.monitoring_start.isoformat(),
                    "reinsertion_date": date.today().isoformat(),
                }

        return False, None

    def process_reinsertion(
        self,
        watch: ReinsertionWatchDB,
        match_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a detected reinsertion.

        AUTHORITY: SYSTEM - Creates violations and triggers escalation AUTOMATICALLY.
        No user confirmation required. User cannot override or cancel escalation.

        Statutory basis:
        - FCRA § 611(a)(5)(B): CRA must provide 5-day notice before reinsertion
        - FCRA § 623(a)(6): Furnisher must not report deleted info without certification
        - FCRA § 616: Willful noncompliance (applies when reinsertion without notice)
        """
        from .state_machine import EscalationStateMachine, AutomaticTransitionTriggers

        # Get the dispute
        dispute = self.db.query(DisputeDB).get(watch.dispute_id)
        if not dispute:
            return {"error": "Dispute not found"}

        # Check for 5-day advance notice
        violations_created = []

        if not watch.notice_received:
            # REINSERTION WITHOUT NOTICE - FCRA § 611(a)(5)(B)
            # AUTHORITY: SYSTEM - Violation created automatically without user confirmation
            violation = {
                "id": str(uuid4()),
                "type": "reinsertion_without_notice",
                "statute": "FCRA § 611(a)(5)(B)",
                "description": "Item previously deleted was reinserted without required 5-day advance notice",
                "severity": "CRITICAL",
                "willful_indicator": True,
                "statute_616_exposure": True,
                "authority": "SYSTEM",  # System-created, not user-reported
                "evidence": {
                    "original_deletion_date": watch.monitoring_start.isoformat(),
                    "reinsertion_date": date.today().isoformat(),
                    "account_fingerprint": watch.account_fingerprint,
                    "notice_received": False,
                }
            }
            violations_created.append(violation)

            # Create furnisher violation if applicable
            # AUTHORITY: SYSTEM - Furnisher violation created automatically
            if watch.furnisher_name:
                furnisher_violation = {
                    "id": str(uuid4()),
                    "type": "furnisher_reinsertion",
                    "statute": "FCRA § 623(a)(6)",
                    "description": f"Furnisher {watch.furnisher_name} re-reported previously deleted information",
                    "severity": "CRITICAL",
                    "willful_indicator": True,
                    "authority": "SYSTEM",  # System-created, not user-reported
                }
                violations_created.append(furnisher_violation)

        # Update watch status
        watch.status = ReinsertionWatchStatus.REINSERTION_DETECTED
        watch.reinsertion_date = date.today()
        watch.reinsertion_violation_id = violations_created[0]["id"] if violations_created else None

        # Create paper trail
        paper_trail = PaperTrailDB(
            id=str(uuid4()),
            dispute_id=dispute.id,
            event_type="reinsertion_detected",
            actor=ActorType.SYSTEM,
            description=f"Reinsertion detected for account {watch.account_fingerprint}. {len(violations_created)} violations created.",
            metadata={
                "watch_id": watch.id,
                "violations_created": len(violations_created),
                "notice_received": watch.notice_received,
                **match_details,
            }
        )
        self.db.add(paper_trail)

        # Trigger automatic escalation to REGULATORY_ESCALATION
        state_machine = EscalationStateMachine(self.db)

        # If dispute was in RESOLVED_DELETED, escalate directly
        if dispute.current_state == EscalationState.RESOLVED_DELETED:
            success, message = AutomaticTransitionTriggers.reinsertion_detected(
                state_machine, dispute
            )
        else:
            # Create escalation log entry
            log_entry = EscalationLogDB(
                id=str(uuid4()),
                dispute_id=dispute.id,
                from_state=dispute.current_state,
                to_state=EscalationState.REGULATORY_ESCALATION,
                trigger="reinsertion_detected",
                actor=ActorType.SYSTEM,
                statutes_activated=["FCRA § 611(a)(5)(B)", "FCRA § 623(a)(6)"],
                violations_created=[v["id"] for v in violations_created],
            )
            self.db.add(log_entry)

            dispute.current_state = EscalationState.REGULATORY_ESCALATION
            success = True
            message = "Escalated to REGULATORY_ESCALATION due to reinsertion"

        return {
            "reinsertion_processed": True,
            "violations_created": violations_created,
            "escalation_triggered": success,
            "escalation_message": message,
            "new_state": dispute.current_state.value,
        }

    def log_reinsertion_notice(
        self,
        watch_id: str,
        notice_date: date,
        notice_content: str = None,
    ) -> Dict[str, Any]:
        """
        Log receipt of a reinsertion notice from user.

        Validates if notice was timely (5 business days before reinsertion).
        """
        watch = self.db.query(ReinsertionWatchDB).get(watch_id)
        if not watch:
            return {"error": "Watch not found"}

        # Check if notice was timely
        # Must be at least 5 business days before reinsertion
        if watch.reinsertion_date:
            # Calculate business days between notice and reinsertion
            required_notice_date = watch.reinsertion_date - timedelta(days=7)  # ~5 business days

            if notice_date <= required_notice_date:
                # Valid notice - timely
                watch.notice_date = notice_date
                watch.notice_received = True

                paper_trail = PaperTrailDB(
                    id=str(uuid4()),
                    dispute_id=watch.dispute_id,
                    event_type="reinsertion_notice_logged",
                    actor=ActorType.USER,
                    description=f"Valid reinsertion notice received dated {notice_date.isoformat()}",
                    metadata={
                        "watch_id": watch_id,
                        "notice_date": notice_date.isoformat(),
                        "notice_timely": True,
                    }
                )
                self.db.add(paper_trail)

                return {
                    "notice_logged": True,
                    "notice_timely": True,
                    "message": "Notice was timely - no violation for lack of notice",
                }
            else:
                # Late notice - still a violation
                watch.notice_date = notice_date
                watch.notice_received = False  # Late notice doesn't count

                violation = {
                    "id": str(uuid4()),
                    "type": "late_reinsertion_notice",
                    "statute": "FCRA § 611(a)(5)(B)(ii)",
                    "description": f"Reinsertion notice received but was late (received {notice_date}, reinsertion {watch.reinsertion_date})",
                    "severity": "HIGH",
                }

                paper_trail = PaperTrailDB(
                    id=str(uuid4()),
                    dispute_id=watch.dispute_id,
                    event_type="late_reinsertion_notice",
                    actor=ActorType.USER,
                    description=f"Late reinsertion notice logged. Notice date: {notice_date.isoformat()}, Reinsertion date: {watch.reinsertion_date.isoformat()}",
                    metadata={
                        "watch_id": watch_id,
                        "notice_date": notice_date.isoformat(),
                        "reinsertion_date": watch.reinsertion_date.isoformat(),
                        "notice_timely": False,
                    }
                )
                self.db.add(paper_trail)

                return {
                    "notice_logged": True,
                    "notice_timely": False,
                    "violation_created": violation,
                    "message": "Notice was late - violation created",
                }
        else:
            # No reinsertion yet - just log the notice for future reference
            watch.notice_date = notice_date
            watch.notice_received = True
            watch.status = ReinsertionWatchStatus.NOTICE_RECEIVED

            return {
                "notice_logged": True,
                "message": "Notice logged - no reinsertion detected yet",
            }

    def run_reinsertion_scan(
        self,
        user_id: str,
        current_accounts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Run reinsertion scan for a user's new report.

        AUTHORITY: SYSTEM - Called automatically during report ingestion.
        User uploads report; system detects reinsertions and creates violations.
        No user confirmation required for violation creation or escalation.

        Called during report ingestion (reports.py upload_report endpoint).
        """
        active_watches = self.get_active_watches(user_id)

        reinsertions_found = []
        reinsertions_processed = []
        errors = []

        for watch in active_watches:
            try:
                is_reinserted, match_details = self.check_for_reinsertion(
                    watch, current_accounts
                )

                if is_reinserted and match_details:
                    reinsertions_found.append(match_details)

                    # Process the reinsertion
                    result = self.process_reinsertion(watch, match_details)
                    reinsertions_processed.append({
                        "watch_id": watch.id,
                        "result": result,
                    })

            except Exception as e:
                errors.append({
                    "watch_id": watch.id,
                    "error": str(e),
                })

        return {
            "scan_date": datetime.utcnow().isoformat(),
            "watches_checked": len(active_watches),
            "reinsertions_found": len(reinsertions_found),
            "reinsertions_processed": len(reinsertions_processed),
            "errors": len(errors),
            "details": {
                "found": reinsertions_found,
                "processed": reinsertions_processed,
                "errors": errors,
            }
        }

    def expire_old_watches(self) -> Dict[str, Any]:
        """
        Expire watches that have passed their monitoring window.
        Called by daily scheduler.
        """
        today = date.today()

        expired_watches = self.db.query(ReinsertionWatchDB).filter(
            ReinsertionWatchDB.status == ReinsertionWatchStatus.ACTIVE,
            ReinsertionWatchDB.monitoring_end < today,
        ).all()

        count = 0
        for watch in expired_watches:
            watch.status = ReinsertionWatchStatus.EXPIRED
            count += 1

        return {
            "expired_count": count,
            "expiration_date": today.isoformat(),
        }
