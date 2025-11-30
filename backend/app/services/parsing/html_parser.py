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
    Bureau, FurnisherType, AccountStatus
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

        report = NormalizedReport(
            consumer=consumer,
            bureau=Bureau.TRANSUNION,  # Default - IdentityIQ is multi-bureau
            report_date=report_date or date.today(),
            accounts=accounts,
            inquiries=inquiries,
            public_records=public_records,
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

            # Find account data table after this header
            account_data = self._extract_account_data_for_header(header)

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
                bureau_account_data = BureauAccountData(
                    bureau=bureau_enum,
                    date_opened=_parse_date(bureau_data.get("date_opened")),
                    date_closed=_parse_date(bureau_data.get("date_closed")),
                    date_of_first_delinquency=_parse_date(bureau_data.get("dofd")),
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
                    payment_history=bureau_data.get("payment_history", []),
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

    def _extract_account_data_for_header(self, header: Tag) -> Dict[str, Dict[str, Any]]:
        """Extract account data for all bureaus from a sub_header block."""
        data = {
            "transunion": {},
            "experian": {},
            "equifax": {}
        }

        next_header = header.find_next('div', class_='sub_header')

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
        """Extract credit inquiries from HTML."""
        inquiries = []

        for tr in soup.find_all('tr'):
            cells = tr.find_all('td', class_='info')

            if len(cells) == 4:
                creditor = cells[0].get_text(strip=True)
                business_type = cells[1].get_text(strip=True)
                inquiry_date = cells[2].get_text(strip=True)

                if not creditor or len(creditor) < 3:
                    continue

                inquiry_type = "hard"
                if "soft" in business_type.lower():
                    inquiry_type = "soft"

                inquiry = Inquiry(
                    creditor_name=creditor,
                    inquiry_date=_parse_date(inquiry_date),
                    inquiry_type=inquiry_type
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
