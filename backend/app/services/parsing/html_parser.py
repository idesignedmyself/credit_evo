"""
Credit Engine 2.0 - IdentityIQ HTML Parser

This parser reads IdentityIQ HTML files and outputs NormalizedReport (SSOT #1).
All downstream modules MUST use NormalizedReport - never raw HTML data.

NEW MODEL: Each Account represents ONE canonical tradeline with bureau-specific
data merged into the `bureaus` dict. This gives us 31 accounts (not 63).
"""
from __future__ import annotations
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup, Tag

from ...models.ssot import (
    NormalizedReport, Account, BureauAccountData, Consumer, Inquiry, PublicRecord,
    Bureau, FurnisherType, AccountStatus, CreditScore,
    PersonalInfo, BureauPersonalInfo, Address, Employer,
    AccountSummary, BureauAccountSummary, CreditorContact
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Regex to validate masked account numbers (e.g., 11107793****, 8986049149KM0****)
# Must contain asterisks (masked) and be alphanumeric, rejecting dates like 04/17/2015
MASKED_ACCOUNT_RE = re.compile(r"^[A-Za-z0-9*]{4,}$")  # Alphanumeric + asterisks only (no slashes, dashes)
STRICT_MASKED_RE = re.compile(r"[0-9]{4,}[*]{2,6}$")  # Strict: digits followed by asterisks

COLLECTION_KEYWORDS = [
    "collection", "coll svcs", "credit collection", "recovery", "assigned",
    "purchased", "sold", "portfolio", "midland", "lvnv", "cavalry", "encore",
    "portfolio recovery", "convergent", "ic system", "transworld"
]

CHARGEOFF_KEYWORDS = [
    "charge off", "chargeoff", "charged off", "charge-off",
    "profit and loss", "written off", "write off", "bad debt"
]

NOT_REPORTED = {"", "-", "—", "–", "N/A", "NOT REPORTED", "NOTREPORTED", "NOT AVAILABLE"}

# Sections to skip (not actual creditor accounts)
NON_ACCOUNT_SECTIONS = {
    "RISK", "RISK FACTORS", "PERSONAL INFORMATION", "ALERTS",
    "ADDRESSES", "ADDRESS HISTORY", "EMPLOYMENT", "INQUIRIES",
    "PUBLIC RECORDS", "CREDIT SCORE", "SCORE FACTORS", "SUMMARY"
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text, returning None if empty or 'not reported'."""
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    # Remove trailing dashes (IdentityIQ formatting artifact)
    text = text.rstrip('-')
    if text.upper() in NOT_REPORTED:
        return None
    return text


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None

    date_str = _clean_text(date_str)
    if not date_str:
        return None

    formats = ["%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y", "%d/%m/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_money(amount_str: Optional[str]) -> Optional[float]:
    """Parse money string to float."""
    if not amount_str:
        return None

    cleaned = _clean_text(amount_str)
    if not cleaned:
        return None

    # Remove currency symbols, commas, spaces
    cleaned = re.sub(r"[$,\s]", "", cleaned)

    # Handle negative amounts in parentheses
    is_negative = cleaned.startswith("(") and cleaned.endswith(")")
    if is_negative:
        cleaned = cleaned[1:-1]

    try:
        value = float(cleaned)
        return -value if is_negative else value
    except ValueError:
        return None


def _parse_int(value_str: Optional[str]) -> Optional[int]:
    """Parse integer string to int."""
    if not value_str:
        return None
    cleaned = _clean_text(value_str)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


# Month name to number mapping for DOFD inference
MONTH_TO_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def _infer_dofd_from_payment_history(payment_history: List[Dict[str, Any]]) -> Optional[date]:
    """
    Infer Date of First Delinquency from payment history.

    Logic:
    1. Payment history is a list like: [{"month": "Jan", "year": 2024, "status": "OK"}, ...]
    2. Statuses are: "OK" (current), "30", "60", "90", "120", "CO" (charge-off), etc.
    3. We find the OLDEST (earliest date) non-OK status
    4. Return that as the inferred DOFD

    This catches cases where the bureau doesn't explicitly report DOFD but
    the payment history shows when delinquency started.
    """
    if not payment_history:
        return None

    # Delinquent statuses (anything that's not OK/current)
    ok_statuses = {"OK", "ok", "Ok", "", "-", None}

    # Find all delinquent months and sort by date (oldest first)
    delinquent_months = []
    for entry in payment_history:
        status = entry.get("status", "")
        if status not in ok_statuses:
            month_str = entry.get("month", "")
            year = entry.get("year")

            if month_str and year:
                month_num = MONTH_TO_NUM.get(month_str.lower()[:3])
                if month_num:
                    try:
                        # Use 1st of the month for DOFD
                        delinquent_months.append(date(int(year), month_num, 1))
                    except (ValueError, TypeError):
                        continue

    if not delinquent_months:
        return None

    # Return the OLDEST delinquency date (earliest in time)
    return min(delinquent_months)


def _classify_furnisher_type(
    creditor_name: str,
    account_type_detail: Optional[str],
    status: Optional[str],
    original_creditor: Optional[str],
    comments: Optional[str]
) -> FurnisherType:
    """Classify furnisher type - THIS IS SSOT, cannot be changed downstream."""
    combined_text = " ".join(filter(None, [
        creditor_name, account_type_detail, status, comments
    ])).lower()

    # Rule 1: Has original creditor = definitely a collector
    if original_creditor and _clean_text(original_creditor):
        return FurnisherType.COLLECTOR

    # Rule 2: Collection keywords in type/name/comments
    if any(keyword in combined_text for keyword in COLLECTION_KEYWORDS):
        return FurnisherType.COLLECTOR

    # Rule 3: Chargeoff status = original creditor who charged off
    if status:
        status_lower = status.lower()
        if any(keyword in status_lower for keyword in CHARGEOFF_KEYWORDS):
            return FurnisherType.OC_CHARGEOFF

    # Rule 4: Default to non-chargeoff original creditor
    return FurnisherType.OC_NON_CHARGEOFF


def _classify_account_status(status_str: Optional[str], comments: Optional[str]) -> AccountStatus:
    """Classify account status from status string."""
    if not status_str:
        return AccountStatus.UNKNOWN

    status_lower = status_str.lower()
    combined = f"{status_lower} {(comments or '').lower()}"

    if "collection" in combined:
        return AccountStatus.COLLECTION
    if "charge" in combined and "off" in combined:
        return AccountStatus.CHARGEOFF
    if "closed" in combined:
        return AccountStatus.CLOSED
    if "paid" in combined:
        return AccountStatus.PAID
    if "open" in combined or "current" in combined:
        return AccountStatus.OPEN
    if any(word in combined for word in ["derogatory", "delinquent", "late"]):
        return AccountStatus.DEROGATORY

    return AccountStatus.UNKNOWN


def _extract_original_creditor(creditor_name: str) -> tuple[str, Optional[str]]:
    """Extract original creditor from creditor name if present."""
    match = re.search(r"\(Original Creditor:\s*([^)]+)\)", creditor_name, re.IGNORECASE)
    if match:
        original = match.group(1).strip()
        clean_name = re.sub(r"\s*\(Original Creditor:[^)]+\)", "", creditor_name).strip()
        return clean_name, original
    return creditor_name, None


def _mask_account_number(account_number: Optional[str]) -> str:
    """Create masked account number showing last 4 digits."""
    if not account_number:
        return ""
    if "*" in account_number or "#" in account_number:
        return account_number
    if len(account_number) > 4:
        return "*" * (len(account_number) - 4) + account_number[-4:]
    return account_number


def _normalize_account_number(text: Optional[str]) -> str:
    """Normalize account number for canonical key matching."""
    if not text:
        return "unknown"
    return text.strip().lower().replace("x", "*")


def _extract_payment_history_from_table(table: Tag) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract Two-Year Payment History from the payment history table.

    Returns dict keyed by bureau name with list of payment entries:
    {
        "transunion": [{"month": "May", "year": 2018, "status": "OK"}, ...],
        "experian": [...],
        "equifax": [...]
    }
    """
    result = {
        "transunion": [],
        "experian": [],
        "equifax": []
    }

    rows = table.find_all('tr')
    if len(rows) < 5:
        return result

    # Row 0: Month labels (from span.lg-view or direct text)
    # Row 1: Year (2-digit)
    # Row 2: TransUnion statuses
    # Row 3: Experian statuses
    # Row 4: Equifax statuses

    months = []
    years = []

    # Extract months from row 0
    month_cells = rows[0].find_all('td', class_='info')
    for cell in month_cells:
        # Try to get month from span.lg-view first
        span = cell.find('span', class_='lg-view')
        if span:
            months.append(span.get_text(strip=True))
        else:
            months.append(cell.get_text(strip=True))

    # Extract years from row 1
    year_cells = rows[1].find_all('td', class_='info')
    for cell in year_cells:
        year_text = cell.get_text(strip=True)
        if year_text:
            try:
                # Convert 2-digit year to 4-digit
                year_int = int(year_text)
                if year_int < 100:
                    year_int = 2000 + year_int if year_int < 50 else 1900 + year_int
                years.append(year_int)
            except ValueError:
                years.append(None)
        else:
            years.append(None)

    # Map row index to bureau
    bureau_rows = {
        2: "transunion",
        3: "experian",
        4: "equifax"
    }

    # Extract status for each bureau
    for row_idx, bureau_name in bureau_rows.items():
        if row_idx >= len(rows):
            continue

        status_cells = rows[row_idx].find_all('td', class_='info')

        for i, cell in enumerate(status_cells):
            if i >= len(months) or i >= len(years):
                continue

            status = cell.get_text(strip=True)
            month = months[i] if i < len(months) else ""
            year = years[i] if i < len(years) else None

            # Only add if we have valid data
            if month and year:
                result[bureau_name].append({
                    "month": month,
                    "year": year,
                    "status": status if status else ""
                })

    return result


def _create_canonical_key(creditor_name: str, account_number: str) -> str:
    """Create canonical key for account deduplication."""
    return f"{creditor_name.lower().strip()}::{_normalize_account_number(account_number)}"


# =============================================================================
# MAIN PARSER CLASS
# =============================================================================

class IdentityIQHTMLParser:
    """
    Parse IdentityIQ HTML reports into NormalizedReport (SSOT #1).

    NEW MODEL: Creates ONE Account per canonical tradeline, with bureau-specific
    data merged into the Account.bureaus dict. This produces 31 accounts (not 63).
    """

    def parse(self, html_path: str) -> NormalizedReport:
        """Parse HTML file and return NormalizedReport."""
        logger.info(f"Parsing HTML file: {html_path}")

        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read HTML file: {e}")
            raise ValueError(f"Cannot read HTML file: {e}")

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract all components
        consumer = self._extract_consumer(soup)
        accounts = self._extract_accounts_merged(soup)
        inquiries = self._extract_inquiries(soup)
        public_records = self._extract_public_records(soup)
        report_date = self._extract_report_date(soup)
        credit_scores = self._extract_credit_scores(soup)
        personal_info = self._extract_personal_info(soup)
        account_summary = self._extract_account_summary(soup)
        creditor_contacts = self._extract_creditor_contacts(soup)

        report = NormalizedReport(
            consumer=consumer,
            bureau=Bureau.TRANSUNION,  # Default - IdentityIQ is multi-bureau
            report_date=report_date or date.today(),
            accounts=accounts,
            inquiries=inquiries,
            public_records=public_records,
            creditor_contacts=creditor_contacts,
            credit_scores=credit_scores,
            personal_info=personal_info,
            account_summary=account_summary,
            source_file=str(html_path)
        )

        logger.info(f"Parsed {len(accounts)} canonical accounts")
        return report

    def _extract_consumer(self, soup: BeautifulSoup) -> Consumer:
        """Extract consumer personal information."""
        names = {"transunion": "", "experian": "", "equifax": ""}
        dobs = {"transunion": None, "experian": None, "equifax": None}
        addresses = {"transunion": "", "experian": "", "equifax": ""}

        for table in soup.find_all('table', class_='rpt_table4column'):
            for tr in table.find_all('tr'):
                label_cell = tr.find('td', class_='label')
                if not label_cell:
                    continue

                label = label_cell.get_text(strip=True)
                info_cells = tr.find_all('td', class_='info')

                if len(info_cells) >= 3:
                    values = [cell.get_text(strip=True) for cell in info_cells[:3]]

                    if 'Name:' in label:
                        names["transunion"] = values[0] if values[0] != '-' else ""
                        names["experian"] = values[1] if values[1] != '-' else ""
                        names["equifax"] = values[2] if values[2] != '-' else ""

                    elif 'Date of Birth' in label:
                        dobs["transunion"] = _parse_date(values[0])
                        dobs["experian"] = _parse_date(values[1])
                        dobs["equifax"] = _parse_date(values[2])

                    elif 'Current Address' in label:
                        addresses["transunion"] = values[0] if values[0] != '-' else ""
                        addresses["experian"] = values[1] if values[1] != '-' else ""
                        addresses["equifax"] = values[2] if values[2] != '-' else ""

        full_name = names["transunion"] or names["experian"] or names["equifax"] or ""
        dob = dobs["transunion"] or dobs["experian"] or dobs["equifax"]
        address = addresses["transunion"] or addresses["experian"] or addresses["equifax"] or ""

        city, state, zip_code = "", "", ""
        if address:
            match = re.search(r",\s*([^,]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)", address)
            if match:
                city = match.group(1).strip()
                state = match.group(2)
                zip_code = match.group(3)

        return Consumer(
            full_name=full_name,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            date_of_birth=dob
        )

    def _extract_accounts_merged(self, soup: BeautifulSoup) -> List[Account]:
        """
        Extract accounts with MERGED bureau data.

        Each sub_header = ONE canonical account.
        Bureau-specific data (TU/EX/EQ columns) is merged into Account.bureaus dict.
        Returns 31 accounts (one per sub_header block).
        """
        accounts = []

        # IdentityIQ-specific selector for actual creditor headers
        # CRITICAL: This exact selector MUST match what we use for boundary detection
        sub_headers = soup.select("div.sub_header.ng-binding.ng-scope")

        for idx, header in enumerate(sub_headers):
            creditor_name = header.get_text(strip=True)

            # Skip non-account headers
            if not creditor_name or len(creditor_name) < 2:
                continue
            if creditor_name.upper() in NON_ACCOUNT_SECTIONS:
                continue
            if any(skip in creditor_name.upper() for skip in ["RISK FACTOR", "PERSONAL INFO"]):
                continue

            # Extract original creditor if present
            clean_name, original_creditor = _extract_original_creditor(creditor_name)

            # FIXED: Pass the exact next header from our list to prevent data bleeding
            # The old code used find_next('div', class_='sub_header') which was too broad
            next_header = sub_headers[idx + 1] if idx + 1 < len(sub_headers) else None

            # Find account data table after this header
            account_data = self._extract_account_data_for_header(header, next_header)

            if not account_data:
                continue

            # Get account number from any bureau that has it
            account_number = ""
            for bureau_name in ["transunion", "experian", "equifax"]:
                if account_data.get(bureau_name, {}).get("account_number"):
                    account_number = account_data[bureau_name]["account_number"]
                    break

            # Create ONE account per sub_header (no cross-header merging)
            account = Account(
                creditor_name=clean_name,
                original_creditor=original_creditor,
                account_number=account_number,
                account_number_masked=_mask_account_number(account_number),
                bureaus={},
            )

            # Add bureau-specific data
            for bureau_name in ["transunion", "experian", "equifax"]:
                bureau_data = account_data.get(bureau_name, {})

                if not bureau_data:
                    continue

                bureau_enum = {
                    "transunion": Bureau.TRANSUNION,
                    "experian": Bureau.EXPERIAN,
                    "equifax": Bureau.EQUIFAX
                }[bureau_name]

                # Create BureauAccountData
                # Get payment history first (needed for DOFD inference)
                payment_history = bureau_data.get("payment_history", [])

                # Try explicit DOFD first, then infer from payment history
                explicit_dofd = _parse_date(bureau_data.get("dofd"))
                inferred_dofd = _infer_dofd_from_payment_history(payment_history) if not explicit_dofd else None
                final_dofd = explicit_dofd or inferred_dofd

                bureau_account_data = BureauAccountData(
                    bureau=bureau_enum,
                    date_opened=_parse_date(bureau_data.get("date_opened")),
                    date_closed=_parse_date(bureau_data.get("date_closed")),
                    date_of_first_delinquency=final_dofd,
                    date_last_activity=_parse_date(bureau_data.get("date_last_active")),
                    date_last_payment=_parse_date(bureau_data.get("date_of_last_payment")),
                    date_reported=_parse_date(bureau_data.get("last_reported")),
                    balance=_parse_money(bureau_data.get("balance")),
                    credit_limit=_parse_money(bureau_data.get("credit_limit")),
                    high_credit=_parse_money(bureau_data.get("high_credit")),
                    past_due_amount=_parse_money(bureau_data.get("past_due")),
                    monthly_payment=_parse_money(bureau_data.get("monthly_payment")),
                    payment_status=bureau_data.get("payment_status"),
                    account_status_raw=bureau_data.get("status"),
                    remarks=bureau_data.get("comments"),
                    bureau_code=bureau_data.get("bureau_code"),
                    term_months=_parse_int(bureau_data.get("term_months")),
                    account_type=bureau_data.get("account_type"),
                    account_type_detail=bureau_data.get("account_type_detail"),
                    payment_history=payment_history,
                )

                account.bureaus[bureau_enum] = bureau_account_data

            # Finalize and append this account
            self._finalize_account(account)
            accounts.append(account)

        logger.info(f"Extracted {len(accounts)} canonical accounts (1 per sub_header)")
        return accounts

    def _finalize_account(self, account: Account) -> None:
        """Populate legacy fields from first bureau with data and classify."""
        if not account.bureaus:
            return

        # Set primary bureau (first one with data)
        primary_bureau = list(account.bureaus.keys())[0]
        account.bureau = primary_bureau

        primary_data = account.bureaus[primary_bureau]

        # Populate legacy fields from primary bureau
        account.date_opened = primary_data.date_opened
        account.date_closed = primary_data.date_closed
        account.date_of_first_delinquency = primary_data.date_of_first_delinquency
        account.date_last_activity = primary_data.date_last_activity
        account.date_last_payment = primary_data.date_last_payment
        account.date_reported = primary_data.date_reported
        account.balance = primary_data.balance
        account.credit_limit = primary_data.credit_limit
        account.high_credit = primary_data.high_credit
        account.past_due_amount = primary_data.past_due_amount
        account.current_balance = primary_data.balance
        account.monthly_payment = primary_data.monthly_payment
        account.payment_status = primary_data.payment_status

        # Set account_type from primary bureau (if not already set)
        if not account.account_type and primary_data.account_type:
            account.account_type = primary_data.account_type

        # Classify furnisher type
        account.furnisher_type = _classify_furnisher_type(
            account.creditor_name,
            account.account_type,
            primary_data.account_status_raw,
            account.original_creditor,
            primary_data.remarks
        )

        # Classify account status
        account.account_status = _classify_account_status(
            primary_data.account_status_raw,
            primary_data.remarks
        )

    def _extract_account_data_for_header(self, header: Tag, next_header: Optional[Tag] = None) -> Dict[str, Dict[str, Any]]:
        """
        Extract account data for all bureaus from a sub_header block.

        FIXED: Now accepts next_header parameter to ensure proper boundary detection.
        This prevents data bleeding between accounts when there are intermediate
        div.sub_header elements without the ng-binding ng-scope classes.
        """
        data = {
            "transunion": {},
            "experian": {},
            "equifax": {}
        }

        for elem in header.find_all_next():
            if elem == next_header:
                break

            # Check for payment history table (Two-Year Payment History)
            if elem.name == 'table' and 'addr_hsrty' in (elem.get('class') or []):
                payment_history = _extract_payment_history_from_table(elem)
                # Add payment history to each bureau's data
                for bureau_name in ["transunion", "experian", "equifax"]:
                    if payment_history.get(bureau_name):
                        data[bureau_name]["payment_history"] = payment_history[bureau_name]

            if elem.name == 'tr':
                # CRITICAL FIX: Only process rows from the main account data table
                # Skip rows from print tables (crPrint) which contain data from other accounts
                parent_table = elem.find_parent('table')
                if parent_table:
                    table_classes = parent_table.get('class', [])
                    # Only process rows from rpt_content_table (the main data table)
                    # Skip crPrint tables which are print preview and show other account data
                    if 'crPrint' in table_classes:
                        continue
                    if 'rpt_content_table' not in table_classes and 'rpt_table4column' not in table_classes:
                        continue

                label_cell = elem.find('td', class_='label')
                if not label_cell:
                    continue

                label = label_cell.get_text(strip=True)
                info_cells = elem.find_all('td', class_='info')

                field_map = {
                    # Core account identifiers
                    "Account #:": "account_number",
                    "Account Type:": "account_type",
                    "Account Type - Detail:": "account_type_detail",
                    "Bureau Code:": "bureau_code",  # e.g., "Individual", "Joint"
                    "Account Status:": "status",
                    # Financial data
                    "Monthly Payment:": "monthly_payment",
                    "Balance:": "balance",
                    "No. of Months (terms):": "term_months",  # Loan term in months
                    "High Credit:": "high_credit",
                    "Credit Limit:": "credit_limit",
                    "Past Due:": "past_due",
                    "Payment Status:": "payment_status",
                    # Dates
                    "Date Opened:": "date_opened",
                    "Last Reported:": "last_reported",
                    "Date Last Active:": "date_last_active",
                    "Date last active:": "date_last_active",
                    "Date of Last Payment:": "date_of_last_payment",
                    "Date of last payment:": "date_of_last_payment",
                    # Optional fields (may not be in all reports)
                    "Comments:": "comments",
                    "Date of First Delinquency:": "dofd",
                    "Date of 1st Delinquency:": "dofd",
                    "DOFD:": "dofd",
                    "First Delinquency:": "dofd",
                    "Date Closed:": "date_closed",
                }

                field_name = None
                for label_pattern, field in field_map.items():
                    if label_pattern.lower() in label.lower():
                        field_name = field
                        break

                if not field_name:
                    continue

                # Process each bureau column (TU, EX, EQ)
                for idx, cell in enumerate(info_cells[:3]):  # Only first 3 columns
                    value = cell.get_text(strip=True)

                    # Skip empty or placeholder values
                    if not value or value in ('-', '—', '–'):
                        continue

                    # CRITICAL: For account_number, only accept masked patterns
                    # This prevents dates like "04/17/2015" from being stored as account numbers
                    if field_name == "account_number":
                        if not MASKED_ACCOUNT_RE.match(value):
                            # Not a valid account number pattern - skip this value
                            logger.debug(f"Rejected invalid account number: '{value}' (doesn't match masked pattern)")
                            continue

                    # Assign to correct bureau based on column index
                    if idx == 0:
                        data["transunion"][field_name] = value
                    elif idx == 1:
                        data["experian"][field_name] = value
                    elif idx == 2:
                        data["equifax"][field_name] = value

        return data

    def _extract_inquiries(self, soup: BeautifulSoup) -> List[Inquiry]:
        """Extract credit inquiries from HTML.

        Columns: Creditor Name | Type of Business | Date of Inquiry | Credit Bureau
        """
        inquiries = []

        for tr in soup.find_all('tr'):
            cells = tr.find_all('td', class_='info')

            if len(cells) == 4:
                creditor = cells[0].get_text(strip=True)
                business_type = _clean_text(cells[1].get_text(strip=True))
                inquiry_date = cells[2].get_text(strip=True)
                bureau_str = _clean_text(cells[3].get_text(strip=True))

                if not creditor or len(creditor) < 3:
                    continue

                inquiry_type = "hard"
                if business_type and "soft" in business_type.lower():
                    inquiry_type = "soft"

                # Map bureau string to Bureau enum
                bureau = None
                if bureau_str:
                    bureau_lower = bureau_str.lower()
                    if 'transunion' in bureau_lower:
                        bureau = Bureau.TRANSUNION
                    elif 'experian' in bureau_lower:
                        bureau = Bureau.EXPERIAN
                    elif 'equifax' in bureau_lower:
                        bureau = Bureau.EQUIFAX

                inquiry = Inquiry(
                    creditor_name=creditor,
                    inquiry_date=_parse_date(inquiry_date),
                    inquiry_type=inquiry_type,
                    type_of_business=business_type,
                    bureau=bureau
                )

                inquiries.append(inquiry)

        return inquiries

    def _extract_public_records(self, soup: BeautifulSoup) -> List[PublicRecord]:
        """Extract public records from HTML."""
        records = []

        for td in soup.find_all('td', class_='none-reported'):
            if 'None Reported' in td.get_text():
                return []

        return records

    def _extract_report_date(self, soup: BeautifulSoup) -> Optional[date]:
        """Extract report date from HTML."""
        for tr in soup.find_all('tr'):
            label_cell = tr.find('td', class_='label')
            if label_cell and 'Credit Report Date' in label_cell.get_text():
                info_cell = tr.find('td', class_='info')
                if info_cell:
                    date_text = info_cell.get_text(strip=True)
                    return _parse_date(date_text)
        return None

    def _extract_credit_scores(self, soup: BeautifulSoup) -> Optional[CreditScore]:
        """
        Extract credit scores from the Credit Score section.

        HTML structure:
        <div id="CreditScore">
            <table class="rpt_table4column">
                <tr>
                    <th></th>
                    <th class="headerTUC">TransUnion</th>
                    <th class="headerEXP">Experian</th>
                    <th class="headerEQF">Equifax</th>
                </tr>
                <tr>
                    <td class="label">Credit Score:</td>
                    <td class="info">562</td>
                    <td class="info">582</td>
                    <td class="info">671</td>
                </tr>
                <tr>
                    <td class="label">Lender Rank:</td>
                    <td class="info">Unfavorable</td>
                    <td class="info">Unfavorable</td>
                    <td class="info">Good</td>
                </tr>
                ...
            </table>
        </div>
        """
        credit_score = CreditScore()
        found_scores = False

        # Try to find the CreditScore section by ID first
        score_section = soup.find('div', id='CreditScore')
        if score_section:
            table = score_section.find('table', class_='rpt_table4column')
        else:
            # Fallback: Look for any table with credit score data
            table = None
            for t in soup.find_all('table', class_='rpt_table4column'):
                for tr in t.find_all('tr'):
                    label_cell = tr.find('td', class_='label')
                    if label_cell and 'Credit Score:' in label_cell.get_text():
                        table = t
                        break
                if table:
                    break

        if not table:
            logger.debug("Credit score table not found")
            return None

        # Parse the table rows
        for tr in table.find_all('tr'):
            label_cell = tr.find('td', class_='label')
            if not label_cell:
                continue

            label = label_cell.get_text(strip=True)
            info_cells = tr.find_all('td', class_='info')

            if len(info_cells) < 3:
                continue

            values = [cell.get_text(strip=True) for cell in info_cells[:3]]

            if 'Credit Score:' in label:
                # Parse scores as integers
                try:
                    if values[0] and values[0] not in ('-', '—', '–', 'N/A'):
                        credit_score.transunion = int(values[0])
                        found_scores = True
                except ValueError:
                    pass
                try:
                    if values[1] and values[1] not in ('-', '—', '–', 'N/A'):
                        credit_score.experian = int(values[1])
                        found_scores = True
                except ValueError:
                    pass
                try:
                    if values[2] and values[2] not in ('-', '—', '–', 'N/A'):
                        credit_score.equifax = int(values[2])
                        found_scores = True
                except ValueError:
                    pass

            elif 'Lender Rank:' in label:
                if values[0] and values[0] not in ('-', '—', '–', 'N/A'):
                    credit_score.transunion_rank = values[0]
                if values[1] and values[1] not in ('-', '—', '–', 'N/A'):
                    credit_score.experian_rank = values[1]
                if values[2] and values[2] not in ('-', '—', '–', 'N/A'):
                    credit_score.equifax_rank = values[2]

            elif 'Score Scale:' in label:
                # Usually "300-850" for all bureaus, just take first non-empty
                for v in values:
                    if v and v not in ('-', '—', '–', 'N/A'):
                        credit_score.score_scale = v
                        break

        if found_scores:
            logger.info(f"Extracted credit scores - TU: {credit_score.transunion}, EX: {credit_score.experian}, EQ: {credit_score.equifax}")
            return credit_score

        return None

    def _extract_personal_info(self, soup: BeautifulSoup) -> Optional[PersonalInfo]:
        """
        Extract detailed personal information for each bureau using CSS selectors.

        Fields extracted per bureau:
        - Credit Report Date
        - Name
        - Also Known As
        - Former (names)
        - Date of Birth
        - Current Address(es)
        - Previous Address(es)
        - Employers

        HTML structure: table.rpt_table4column with 3 td.info cells per row (TU, EX, EQ)
        """
        personal_info = PersonalInfo()

        # Initialize bureau data
        bureau_data = {
            Bureau.TRANSUNION: BureauPersonalInfo(bureau=Bureau.TRANSUNION),
            Bureau.EXPERIAN: BureauPersonalInfo(bureau=Bureau.EXPERIAN),
            Bureau.EQUIFAX: BureauPersonalInfo(bureau=Bureau.EQUIFAX),
        }

        bureaus_list = [Bureau.TRANSUNION, Bureau.EXPERIAN, Bureau.EQUIFAX]

        # CSS selector for the Personal Information section
        # Path: #ctrlCreditReport > transunion-report > div.ng-binding.ng-scope > div:nth-child(7)
        # This section contains a table with 3 columns: TransUnion, Experian, Equifax
        personal_section = soup.select_one(
            '#ctrlCreditReport > transunion-report > div.ng-binding.ng-scope > div:nth-child(7)'
        )

        # Fallback to first rpt_table4column if specific path not found
        if personal_section:
            personal_table = personal_section.select_one('table.rpt_table4column')
        else:
            personal_table = soup.select_one('table.rpt_table4column')

        if personal_table:
            # Process each row in the personal info table
            for row in personal_table.select('tr'):
                label_cell = row.select_one('td.label')
                if not label_cell:
                    continue

                label = label_cell.get_text(strip=True)
                info_cells = row.select('td.info')

                if len(info_cells) < 3:
                    continue

                # Get values for each bureau (columns: TU, EX, EQ)
                values = [_clean_text(cell.get_text(strip=True)) for cell in info_cells[:3]]

                # Map labels to fields
                if 'Credit Report Date' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].credit_report_date = _parse_date(values[i])

                elif label == 'Name:' or 'Name (Primary)' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].name_primary = values[i]

                elif 'Also Known As' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            # Multiple AKAs may be separated by newlines in the cell
                            akas = [a.strip() for a in values[i].split('\n') if a.strip() and a.strip() != '-']
                            bureau_data[bureau].also_known_as = akas

                elif label == 'Former:' or 'Former Name' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            formers = [f.strip() for f in values[i].split('\n') if f.strip() and f.strip() != '-']
                            bureau_data[bureau].former_names = formers

                elif 'Date of Birth' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            # Store raw value for partial dates (e.g., "1975" from Experian)
                            bureau_data[bureau].date_of_birth_raw = values[i]
                            # Also try to parse as full date
                            bureau_data[bureau].date_of_birth = _parse_date(values[i])

                elif 'Current Address' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            # Multiple addresses may be in the same cell, separated by newlines
                            addr_lines = [a.strip() for a in values[i].split('\n') if a.strip() and a.strip() != '-']
                            for addr_text in addr_lines:
                                address = Address(full_address=addr_text, address_type="current")
                                self._parse_address_components(address)
                                bureau_data[bureau].current_addresses.append(address)

                elif 'Previous Address' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            addr_lines = [a.strip() for a in values[i].split('\n') if a.strip() and a.strip() != '-']
                            for addr_text in addr_lines:
                                address = Address(full_address=addr_text, address_type="previous")
                                self._parse_address_components(address)
                                bureau_data[bureau].previous_addresses.append(address)

                elif 'Employer' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            emp_lines = [e.strip() for e in values[i].split('\n') if e.strip() and e.strip() != '-']
                            for emp_name in emp_lines:
                                employer = Employer(name=emp_name)
                                bureau_data[bureau].employers.append(employer)

        # Build the PersonalInfo object
        personal_info.bureaus = bureau_data

        # Set canonical values (pick first non-empty from TU > EX > EQ)
        for bureau in bureaus_list:
            if bureau_data[bureau].name_primary and not personal_info.canonical_name:
                personal_info.canonical_name = bureau_data[bureau].name_primary
            if bureau_data[bureau].date_of_birth and not personal_info.canonical_dob:
                personal_info.canonical_dob = bureau_data[bureau].date_of_birth

        # Collect all unique names
        all_names_set = set()
        for bureau in bureau_data.values():
            if bureau.name_primary:
                all_names_set.add(bureau.name_primary)
            all_names_set.update(bureau.also_known_as)
            all_names_set.update(bureau.former_names)
        personal_info.all_names = list(all_names_set)

        # Collect all addresses (deduplicated by full_address)
        seen_addresses = set()
        for bureau in bureau_data.values():
            for addr in bureau.current_addresses + bureau.previous_addresses:
                if addr.full_address and addr.full_address not in seen_addresses:
                    seen_addresses.add(addr.full_address)
                    personal_info.all_addresses.append(addr)

        # Collect all employers (deduplicated by name)
        seen_employers = set()
        for bureau in bureau_data.values():
            for emp in bureau.employers:
                if emp.name and emp.name not in seen_employers:
                    seen_employers.add(emp.name)
                    personal_info.all_employers.append(emp)

        logger.info(f"Extracted personal info - Name: {personal_info.canonical_name}, "
                   f"Addresses: {len(personal_info.all_addresses)}, "
                   f"Employers: {len(personal_info.all_employers)}")
        return personal_info

    def _extract_account_summary(self, soup: BeautifulSoup) -> Optional[AccountSummary]:
        """
        Extract account summary statistics for each bureau using CSS selectors.

        Fields extracted per bureau:
        - Total Accounts
        - Open Accounts
        - Closed Accounts
        - Delinquent
        - Derogatory
        - Collection
        - Balances
        - Payments
        - Public Records
        - Inquiries (2 years)

        CSS Path: #ctrlCreditReport > transunion-report > div.ng-binding.ng-scope > div:nth-child(11) > table.re-even-odd.rpt_content_table.rpt_content_header.rpt_table4column
        """
        account_summary = AccountSummary()

        # Initialize bureau data
        bureau_data = {
            Bureau.TRANSUNION: BureauAccountSummary(bureau=Bureau.TRANSUNION),
            Bureau.EXPERIAN: BureauAccountSummary(bureau=Bureau.EXPERIAN),
            Bureau.EQUIFAX: BureauAccountSummary(bureau=Bureau.EQUIFAX),
        }

        bureaus_list = [Bureau.TRANSUNION, Bureau.EXPERIAN, Bureau.EQUIFAX]

        # CSS selector for the Account Summary section
        summary_table = soup.select_one(
            '#ctrlCreditReport > transunion-report > div.ng-binding.ng-scope > div:nth-child(11) > '
            'table.re-even-odd.rpt_content_table.rpt_content_header.rpt_table4column'
        )

        if not summary_table:
            # Fallback: find any table with these classes that has summary-like content
            for table in soup.select('table.rpt_table4column'):
                text = table.get_text(strip=True).lower()
                if 'total accounts' in text or 'open accounts' in text:
                    summary_table = table
                    break

        if summary_table:
            # Process each row in the summary table
            for row in summary_table.select('tr'):
                label_cell = row.select_one('td.label')
                if not label_cell:
                    continue

                label = label_cell.get_text(strip=True).lower()
                info_cells = row.select('td.info')

                if len(info_cells) < 3:
                    continue

                # Get values for each bureau (columns: TU, EX, EQ)
                values = [_clean_text(cell.get_text(strip=True)) for cell in info_cells[:3]]

                # Map labels to fields
                if 'total accounts' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].total_accounts = self._parse_int(values[i])

                elif 'open accounts' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].open_accounts = self._parse_int(values[i])

                elif 'closed accounts' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].closed_accounts = self._parse_int(values[i])

                elif 'delinquent' in label and 'non' not in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].delinquent = self._parse_int(values[i])

                elif 'derogatory' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].derogatory = self._parse_int(values[i])

                elif 'collection' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].collection = self._parse_int(values[i])

                elif 'balance' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].balances = _parse_money(values[i])

                elif 'payment' in label and 'history' not in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].payments = _parse_money(values[i])

                elif 'public record' in label:
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].public_records = self._parse_int(values[i])

                elif 'inquir' in label:  # inquiries, inquiry
                    for i, bureau in enumerate(bureaus_list):
                        if values[i]:
                            bureau_data[bureau].inquiries_2_years = self._parse_int(values[i])

        # Build the AccountSummary object
        account_summary.bureaus = bureau_data

        # Log summary
        tu = bureau_data[Bureau.TRANSUNION]
        logger.info(f"Extracted account summary - TU: {tu.total_accounts} total, "
                   f"{tu.open_accounts} open, {tu.derogatory} derogatory")
        return account_summary

    def _extract_creditor_contacts(self, soup: BeautifulSoup) -> List[CreditorContact]:
        """
        Extract creditor contact information from HTML.

        Columns: Creditor Name | Address | Phone
        Identified by phone number pattern in 3rd column: (XXX) XXX-XXXX
        """
        contacts = []
        seen_creditors = set()
        phone_pattern = re.compile(r'\(\d{3}\)\s*\d{3}-\d{4}')

        for tr in soup.find_all('tr'):
            cells = tr.find_all('td')

            # Creditor contacts table has 3 columns with phone in 3rd
            if len(cells) == 3:
                phone_raw = cells[2].get_text(strip=True)

                # Only process rows where 3rd column has phone number pattern
                if not phone_pattern.search(phone_raw):
                    continue

                creditor_name = _clean_text(cells[0].get_text(strip=True))
                address_raw = cells[1].get_text(strip=True)
                phone = _clean_text(phone_raw)

                # Skip if no creditor name
                if not creditor_name or len(creditor_name) < 3:
                    continue

                # Skip duplicates
                if creditor_name in seen_creditors:
                    continue
                seen_creditors.add(creditor_name)

                # Parse address - format: "STREET ADDRESSCITY,ST ZIP"
                # Clean up non-breaking spaces
                address_raw = address_raw.replace('\xa0', ' ')
                address_str = _clean_text(address_raw)

                # Try to extract city, state, zip from address
                city = None
                state = None
                zip_code = None
                street = address_str

                if address_str:
                    # Pattern: ends with "CITY,ST ZIP" or "CITY, ST ZIP"
                    match = re.search(r',\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)$', address_str)
                    if match:
                        state = match.group(1)
                        zip_code = match.group(2)
                        # Everything before the match is street + city
                        before_match = address_str[:match.start()]
                        # Try to split city from street (city is usually right before comma)
                        city_match = re.search(r'([A-Z][A-Z\s]+)$', before_match)
                        if city_match:
                            city = city_match.group(1).strip()
                            street = before_match[:city_match.start()].strip()
                        else:
                            street = before_match.strip()

                contact = CreditorContact(
                    creditor_name=creditor_name,
                    address=street,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=phone
                )
                contacts.append(contact)

        logger.info(f"Extracted {len(contacts)} creditor contacts")
        return contacts

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse string to int, handling commas and cleaning."""
        if not value:
            return None
        try:
            # Remove commas and any non-numeric characters except minus sign
            cleaned = re.sub(r'[^\d-]', '', value)
            return int(cleaned) if cleaned else None
        except ValueError:
            return None

    def _parse_address_components(self, address: Address) -> None:
        """Parse address string into components (street, city, state, zip)."""
        if not address.full_address:
            return

        # IdentityIQ format: "STREET ADDRESSCITY, STZIP" (sometimes no comma/space)
        # Try multiple patterns
        patterns = [
            # Standard: "123 Main St, City, ST 12345"
            r"(.+?),\s*([^,]+),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)",
            # No comma before state: "123 Main StCity, ST12345"
            r"(.+?)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\s*(\d{5}(?:-\d{4})?)",
            # Compact: "123 MAIN STNEW YORK, NY10026"
            r"(.+?)([A-Z\s]+),\s*([A-Z]{2})(\d{5}(?:-\d{4})?)",
        ]

        for pattern in patterns:
            match = re.match(pattern, address.full_address)
            if match:
                address.street = match.group(1).strip()
                address.city = match.group(2).strip()
                address.state = match.group(3)
                address.zip_code = match.group(4)
                break


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def parse_identityiq_html(html_path: str) -> NormalizedReport:
    """
    Factory function to parse IdentityIQ HTML file.

    Returns NormalizedReport with MERGED accounts (one per canonical tradeline).
    """
    parser = IdentityIQHTMLParser()
    return parser.parse(html_path)
