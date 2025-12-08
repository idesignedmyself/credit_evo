metro2 

The Metro 2® Format: Comprehensive Data Specifications, Regulatory Architecture, and Field-Level Logic for Consumer Credit Reporting
1. Executive Overview of the Consumer Reporting Ecosystem
The modern financial ecosystem is underpinned by the seamless exchange of data between creditors (Data Furnishers) and Consumer Reporting Agencies (CRAs). This exchange is not merely a technical transaction; it is the bedrock of credit risk assessment, interest rate determination, and compliance with federal statutes such as the Fair Credit Reporting Act (FCRA), the Fair Credit Billing Act (FCBA), and the Equal Credit Opportunity Act (ECOA). The mechanism for this exchange is the Metro 2® Format, a standard developed by the Consumer Data Industry Association (CDIA) to ensure the consistency, accuracy, and integrity of consumer credit files.1
The Metro 2® format is the sole industry standard for reporting consumer credit data. Unlike its predecessor, the original Metro format, Metro 2® is designed to handle the complexity of modern credit products, variable payment structures, and the rigorous demands of regulatory compliance. It allows for the reporting of detailed payment history (up to 24 months), specific transaction types, and nuanced indicators for bankruptcy, disputes, and deferments.1
For data furnishers—ranging from multinational banks and credit card issuers to local credit unions, auto lenders, and debt collection agencies—strict adherence to the Metro 2® specification is not optional. It is a prerequisite for data acceptance by the four major CRAs (Equifax, Experian, TransUnion, and Innovis). Deviations from the standard result in data rejection, "mixed files" (where one consumer's data is merged with another's), and significant legal liability under the FCRA for furnishing inaccurate information.1
This report serves as an exhaustive technical reference and operational guide to the Metro 2® format. It deconstructs the logical architecture of the file, dissects the specific alphanumeric codes required for critical fields, and analyzes the downstream implications of reporting decisions on consumer credit scores and regulatory compliance.
2. The Architectural Structure of a Metro 2® Transmission
To understand which codes apply, one must first understand where they reside. The Metro 2® format is a fixed-block, variable-length logical record structure. While the physical transmission characteristics (often EBCDIC or ASCII depending on the mainframe environment) are handled by the transmission software, the logical organization of data is paramount for the compliance officer and data architect.
A standard Metro 2® transmission file is hierarchical. It does not consist of a flat list of accounts but rather a structured sequence of records that define the data furnisher, the accounting period, and the individual consumer trade lines.
2.1 The Record Hierarchy
The file is constructed of four distinct record types, processed sequentially:
Header Record: The "envelope" of the file. It appears once at the very beginning of the transmission. It identifies the data furnisher (via the Transmitting Subscriber Code), the Activity Date (reporting period), and the software vendor used to generate the file. Critical validation occurs here; if the Header Record is malformed, the entire file is rejected by the CRA.4
Base Segment: The "heart" of the reporting structure. Every single consumer account reported must have exactly one Base Segment. This segment is 426 bytes (or 366 bytes in older packed formats) and contains the primary consumer’s identification (Name, SSN, Address) and the core financial data of the account (Balance, Status, Terms, Payment History). It is the only mandatory segment for an account record.5
Appendage Segments: These are conditional segments that "attach" to a Base Segment to provide supplemental information. They cannot exist independently. They handle complex scenarios such as joint account holders, sold loans, or mortgage-specific data.
J1 Segment: Associated Consumer (Same Address). Used for co-signers or joint holders living with the primary borrower.4
J2 Segment: Associated Consumer (Different Address). Used for co-signers living elsewhere.4
K1 Segment: Original Creditor Name. Mandatory for collection agencies to establish the debt's lineage.4
K2 Segment: Purchased From/Sold To. facilitating portfolio transfers.9
K3 Segment: Mortgage Information. Captures secondary market data like agency identifiers.5
K4 Segment: Specialized Payment Information. Used for balloons and deferred payments.5
L1 Segment: Account Number Change. Preserves history when an account number changes.4
N1 Segment: Employment Information. (Rarely used in modern reporting but available).4
Trailer Record: The "seal" of the file. It contains control totals (e.g., total number of records, total sum of balances). The CRAs use this to verify that data was not truncated during transmission.
2.2 Segment sequencing and Logic
The integrity of the file relies on the "Packed" or "Character" format logic. In the standard Character format, the Base Segment is immediately followed by any applicable appendage segments for that specific account, before moving to the next Base Segment.
Example Sequence:
[Header]
-> -> ->
``
Furnishers must configure their software to generate these appendages only when the specific condition (e.g., a joint borrower exists) is met. Reporting empty appendage segments is a violation of the standard and causes processing errors.10
3. The Base Segment: Detailed Field Analysis and Code Logic
The Base Segment contains the most critical data points that drive credit scoring and risk analysis. The proper selection of codes in this segment is the primary determinant of data quality.
3.1 Processing Indicators and Identification
Block Descriptor Word and Record Descriptor Word
While technical, these fields define the length of the record. In a fixed 426-byte Base Segment, these ensure the reading software knows where one account ends and the next begins.
Identification Number (Field 5)
This is the internal account number maintained by the furnisher.
Implication: This number must be unique and persistent. If a furnisher changes their internal system and renumbers accounts, they generally cannot simply report the new number; they must use the L1 Segment to link the old number to the new number. Failing to do so deletes the old trade line (loss of history for the consumer) and creates a new, "young" trade line, effectively lowering the consumer's Average Age of Accounts score.5
3.2 Portfolio Type (Field 8)
The Portfolio Type is a high-level classifier that tells the CRA's system which validation rules to apply to the rest of the segment. It defines the "species" of the credit product. Selecting the wrong Portfolio Type is a foundational error that triggers cascading validation failures.11
The valid codes are mutually exclusive and strictly defined:
Code
Description
Detailed Operational Definition
C
Line of Credit
Non-card revolving accounts. Examples include Personal Lines of Credit (PLOC), Overdraft Lines, or Home Equity Lines of Credit (HELOCs) in some systems (though HELOCs often use 'R' or specific account types). The expectation is a variable balance with a credit limit.
I
Installment
Loans with a fixed number of payments, a fixed maturity date, and typically a fixed payment amount. Examples: Auto loans, Student loans, Personal term loans. The "Terms Duration" field must be populated with the number of months.
M
Mortgage
Real Estate loans. This code triggers the expectation of K3 Segment data (Agency/MIN). It subjects the account to specific RESPA and mortgage servicing standards in reporting.
O
Open Account
Accounts where the entire balance is due at the end of the billing cycle. Examples: American Express Green/Gold cards (charge cards), Utility accounts, Telecom accounts. These are not revolving; carrying a balance is technically a delinquency or a specific "Pay Over Time" feature.
R
Revolving
Accounts with a variable balance, a credit limit, and an option to pay a minimum amount while revolving the remainder. The quintessential example is the Credit Card.

Insight on Portfolio Logic:
The distinction between R (Revolving) and C (Line of Credit) is subtle but significant. Credit scoring models may weigh utilization on "Credit Cards" (R) differently than "Lines of Credit" (C). Furthermore, reporting an Installment Loan (I) requires the reporting of a "Scheduled Monthly Payment Amount," whereas Revolving accounts (R) often calculate the "Scheduled Payment" as the Minimum Amount Due.
3.3 Account Type (Field 9)
While Portfolio Type defines the structure, Account Type defines the specific product. This code provides the granularity required for segmentation. For instance, an "Installment" portfolio could contain both "Auto Loans" and "Student Loans"—two products with vastly different risk profiles and repayment behaviors.11
Furnishers must map their internal product codes to one of the dozens of available Metro 2® Account Types. Below is a comprehensive analysis of the most relevant codes:
Mortgage and Real Estate
19 (FHA Real Estate Mortgage): Federal Housing Administration loans.
25 (VA Real Estate Mortgage): Veterans Affairs loans.
26 (Conventional Real Estate Mortgage): Standard bank mortgages (Fannie/Freddie conforming).
5A (Real Estate - Junior Liens): Second mortgages or non-purchase money firsts.
89 (Home Equity Line of Credit - HELOC): A hybrid product. Often reported with Portfolio Type R (Revolving) or C, but identified specifically as Account Type 89.
Automotive
00 (Auto Loan): Standard purchase finance.
3A (Auto Lease): Differentiates leasing from lending. Leases have different implications for "Balance" (often the residual + remaining payments) vs Loans (principal).
13 (Lease - Non-Auto): Equipment leases, solar panel leases, etc.
Unsecured and Credit Cards
01 (Unsecured Loan): Personal loans.
18 (Credit Card): Standard bank cards.
07 (Charge Account): Retail store cards (e.g., Macy's, Target) that may or may not be revolving.
37 (Combined Credit Plan): Used when a single account number covers multiple sub-products (e.g., a checking account with a credit line), though this is less common in modern segmented reporting.
Collections and Debt Purchase
This is a critical area for compliance. The Account Type determines whether the "Date Opened" is the date of the loan or the date of the assignment.
48 (Collection Agency/Attorney): Used by third-party collectors. Crucial Rule: When reporting Type 48, the K1 Segment (Original Creditor) is mandatory. The "Date Opened" is the date the agency received the file, not the date the consumer took out the original loan.
0C (Debt Purchaser): Used by entities that buy debt (Factoring Companies). Similar to collections, but implies ownership.
Student Loans
12 (Education Loan): Covers both private and federal student loans. Note that for federal loans, the Portfolio Type is almost always I (Installment), but the payment status may be complicated by deferments (Special Comment Codes).
Operational Warning: Using a generic code like 01 (Unsecured) for a specific product like a 12 (Student Loan) can harm the consumer, as student loans often have specific protections and scoring treatments that generic loans do not.
3.4 Date Fields: The Temporal Framework
Dates in Metro 2® follow the strictly defined MMDDYYYY format. Four specific date fields govern the "lifecycle" of the trade line.11
Date Opened (Field 10): The inception of the legal obligation.
For Original Creditors: The date the note was signed.
For Debt Buyers (0C): The date the debt was purchased.
For Collections (48): The date of assignment.
Date of Last Payment (Field 25):
This is the date the last actual funds were applied to the account.
Relevance: It is critical for the "Statute of Limitations" for legal collection (which differs by state) and helps verify the "Date of First Delinquency." If an account is listed as "Current" but the Date of Last Payment is two years ago, it triggers a validation warning (unless it is in a deferred status).
Date Closed (Field 15):
Used only when the account is actually finalized (Paid, Charged-off, Transferred).
Validation: An account with a "Current" status (11) generally should not have a Date Closed unless it was just paid off in the current cycle.
FCRA Compliance Date / Date of First Delinquency (DOFD) (Field 26):
Regulatory Gravity: This is arguably the most legally sensitive field in the entire file. Under the FCRA, negative information (late payments, collections, charge-offs) can generally only remain on a credit report for 7 years plus 180 days from the commencement of the delinquency that immediately preceded the collection activity.
Definition: The month and year the account first went past due and never returned to current.
Immutability: Once established, this date must not change. If a debt is sold to a collector, the collector must report the original DOFD from the original creditor's files. "Re-aging" this date (updating it to the date of purchase) to keep a debt on a credit report longer is illegal.15
Logic: If Account Status is 71, 78, 80, 82, 83, 84, 93, 94, 95, 96, or 97, the DOFD must be populated. If the Account Status is 11 (Current), this field must be blank (filled with zeros/spaces).12
3.5 ECOA Code (Field 37)
The Equal Credit Opportunity Act (ECOA) Code defines the "Who." It tells the CRA which consumer credit file receives the data. This field is the primary driver of "Mixed File" disputes.5

Code
Definition
Liability & Reporting Logic
1
Individual
The consumer has sole contractual liability. Reported on one file.
2
Joint Contractual Liability
Two or more consumers are contractually liable. The account appears on both files. Furnishers usually report two Base Segments (one for each) or one Base with a J1/J2 segment, depending on the software architecture.
3
Authorized User
The consumer is permitted to use the account (e.g., a spouse on a credit card) but is not contractually liable for the debt. Note: While reporting Authorized Users helps build credit, Snippet 5 notes that some furnishers avoid reporting them to avoid disputes if the authorized user claims they aren't responsible for the debt. However, CDIA guidelines generally encourage reporting to support credit inclusion.
5
Co-Maker / Guarantor
The consumer is secondarily liable if the primary maker defaults.
7
Maker
The primary borrower in a Co-Maker situation.
T
Terminated
The association is ended. The trade line stops updating for this consumer.
W
Business/Commercial
Used for commercial accounts where the individual is personally liable. Critical: Many consumer scoring models exclude "W" accounts from utilization ratios, preventing a business line of credit from ruining a personal credit score.17
X
Deceased
The consumer has died. This code acts as a "hard stop" for many marketing activities and flags the file for fraud prevention.
Z
Delete Consumer
Used to remove a consumer from an account they were erroneously associated with.

4. Account Status and Payment Rating: The Health Matrix
The interaction between Account Status (Field 17A) and Payment Rating (Field 17B) forms the core narrative of the account's performance. These fields must be synchronized; a mismatch here is the most common cause of data rejection.8
4.1 Account Status Codes (Field 17A)
The Account Status code reflects the standing of the account as of the compilation of the file.
The "Good" Standings
11 (Current): The account is active, and payments are up to date (0-29 days past due).
Constraint: If Status is 11, Amount Past Due must be zero.
13 (Paid or Closed): The account has been paid in full or closed with a zero balance.
Constraint: Current Balance must be zero. Amount Past Due must be zero. Date Closed must be populated.
The Delinquency Ladder (Active)
Metro 2® defines delinquency strictly by "days past due" buckets.
71: 30–59 days past due.
78: 60–89 days past due.
80: 90–119 days past due.
82: 120–149 days past due.
83: 150–179 days past due.
84: 180+ days past due.
The Derogatory and Terminal Statuses
These codes indicate a breakdown in the contractual relationship.
93 (Collections): Account assigned to internal or external collections.
94 (Foreclosure Completed): The property has been seized and sold.
95 (Voluntary Surrender): The consumer voluntarily returned the collateral (e.g., giving back the car keys). This is negative, but slightly less severe than a repossession in some qualitative reviews.
96 (Repossession): The creditor seized the collateral involuntarily.
97 (Charge-off): The creditor has written the debt off as a loss.
Constraint: The Original Charge-off Amount field must be populated. The Current Balance stays at the amount owed unless the debt is sold or paid.
The "Paid Derogatory" Statuses
When a consumer pays off a defaulted account, the status must change to reflect "Paid" while preserving the history of the default. You cannot go back to Status 13 (Paid/Good) from a Charge-off; you must use the specific "Paid Derogatory" codes 8:
61: Paid Voluntary Surrender.
62: Paid Collection.
63: Paid Repossession.
64: Paid Charge-off.
65: Paid Foreclosure.
Insight on Status 64 vs 97: A common error is leaving an account at Status 97 after the consumer pays it. This results in the consumer continuing to show a balance on a charged-off debt, double-penalizing them. The correct procedure is to update Status to 64, set Balance to 0, and update the Date of Last Payment.8
4.2 Payment Rating (Field 17B)
The Payment Rating field is context-dependent. It is not used for active accounts (Status 11, 71-84) because the status itself tells the story. It is used primarily to "lock in" the severity of the account at the time it was closed or rated.13
Usage Rule: Required when Account Status is 13 (Paid), 65 (Paid Foreclosure), or any of the 88-97 terminal statuses.
The Codes:
0: Current (0-29 days late).
1: 30-59 days late.
2: 60-89 days late.
3: 90-119 days late.
4: 120-149 days late.
5: 150-179 days late.
6: 180+ days late.
G: Collection.
L: Charge-off.
Scenario Example: A consumer pays off a Collection Account.
Old Report: Status 93 (Collection), Balance $500.
New Report: Status 62 (Paid Collection), Balance $0, Payment Rating G.
Why G? Because even though the account is paid (Status 62), the Payment Rating G reminds the scoring model that this was a collection account, not a standard paid loan.
5. The Payment History Profile (The "Grid")
Field 18, the Payment History Profile, is a 24-byte alphanumeric string that provides a rolling window of the account's behavior over the last two years. This is arguably the most valuable data for trend analysis.
5.1 Structure of the Grid
The field consists of 24 positions.
Position 1: The status for the current reporting cycle (previous month).
Position 2: The status for the month prior.
...
Position 24: The status for 24 months ago.
5.2 Valid Grid Codes
The codes allowed in the grid differ slightly from the Account Status codes. They are single characters.5
Grid Code
Definition
Context
0
Current (0-29 days)
Used for on-time payments.
1
30-59 days past due
Corresponds to Status 71.
2
60-89 days past due
Corresponds to Status 78.
3
90-119 days past due
Corresponds to Status 80.
4
120-149 days past due
Corresponds to Status 82.
5
150-179 days past due
Corresponds to Status 83.
6
180+ days past due
Corresponds to Status 84.
B
No history available
Used when the account was not yet open or data is missing. Constraint: "B" cannot be embedded. You cannot have "00B00". It must be trailing: "0000BBBB".
D
No history available this month
Used for gaps in billing, e.g., a deferred student loan where no bill was sent for a month. "00D00" is valid.
E
Zero Balance and Current
Specific to Revolving/Lines of Credit to indicate inactivity with no balance.
G
Collection


H
Foreclosure


J
Voluntary Surrender


K
Repossession


L
Charge-off



Correction Logic: The grid allows for "automated" correction. If a furnisher mistakenly reported a "1" (30-day late) in January, and in February they report a grid starting with "00...", the CRA system will overwrite the January "1" with the "0" from the second position of the new grid. This "self-healing" mechanism reduces the volume of manual dispute forms (AUDs) required.5
6. Regulatory Flags: Compliance and Special Comments
Beyond the raw financial data, Metro 2® includes fields specifically designed to handle the complex regulatory overlays of the FCRA and disaster scenarios.
6.1 Compliance Condition Codes (Field 20)
These two-character codes are mandatory when a consumer disputes data. Failure to report them is a direct violation of the FCRA.13
XB (Dispute - FCRA): Used when a consumer challenges the accuracy of information. The furnisher must report this code immediately upon receiving the dispute (via e-OSCAR or direct mail) and maintain it while the investigation is active.
XC (Dispute Resolved - Disagreement): The investigation is done, the furnisher verified the data is correct, but the consumer still disagrees. This keeps the dispute note on the file.
XH (Dispute Resolved): Used to clear the XB flag when the dispute is resolved or the consumer withdraws it.
XR: Explicitly removes the previous Compliance Condition Code.
XA (Closed by Consumer): Indicates the account was closed voluntarily by the borrower. This is a neutral/positive closure, distinct from "Closed by Credit Grantor."
6.2 Special Comment Codes (Field 19)
These codes provide narrative context. They explain why an account status might look the way it does.13
AW (Natural Disaster): Critical Code. Used during hurricanes, wildfires, or pandemics (like COVID-19). When applied, it signals to scoring models that delinquencies during this period may be anomalous. CDIA guidance suggests reporting AW with a "Current" status (11) if an accommodation is made, effectively "freezing" the negative reporting during the disaster.1
AC (Partial Payment Agreement): Used when a lender agrees to accept less than the full payment (e.g., a troubled debt restructuring).
AI (Active Military Duty): Flags the account for Servicemembers Civil Relief Act (SCRA) protections.
B (Credit Counseling): Indicates the consumer is in a debt management plan. While the FCRA prohibits using this code as the sole basis for denying credit, some lenders view it as a sign of financial distress.
M (Closed by Credit Grantor): Used when the bank closes the account (e.g., for inactivity or high risk). This can have a negative impact compared to XA.
BN (Closed due to Inactivity): A newer code providing a specific reason for issuer closure, distinguishing it from risk-based closures.
6.3 Consumer Information Indicators (Field 38)
This field handles Bankruptcy and Consumer Statements. It is a heavy-weight flag that overrides most other data.23
Chapter 7 (Liquidation):
A: Petition Filed. (Stops collection activity).
E: Discharged. (Debt is wiped out). Constraint: Balance must be reported as 0.
I: Dismissed. (Bankruptcy failed; debt is reinstated).
Chapter 13 (Wage Earner Plan):
D: Petition Filed.
H: Discharged (Completed).
L: Dismissed.
Q: Removes a previously reported bankruptcy indicator.
Bankruptcy Reporting Logic: When a consumer files for bankruptcy (Code A or D), the account typically freezes. When Discharged (Code E or H), the Balance must be zeroed out. Reporting a balance on a discharged debt is a major compliance violation (violation of the discharge injunction).
7. Appendage Segments: The "Variable" Data
To fully satisfy the requirement for a "nuanced understanding," one must master the appendage segments. These handle the non-standard scenarios.
7.1 K1 Segment: Original Creditor Name
Mandatory for Collection Agencies. When a debt buyer (Account Type 0C) or Collection Agency (Type 48) reports a trade line, the consumer has a right to know who they originally owed. The K1 segment stores the name of the original bank or issuer (e.g., "Chase Bank," "Verizon"). Without this, the trade line is unverifiable.4
7.2 K2 Segment: Portfolio Transfers
Used when loans are sold.
Scenario: Bank A sells a mortgage to Bank B.
Bank A Reports: Status DA (Delete) or Transfer, and a K2 Segment with Indicator 2 (Sold To) and Bank B’s name.
Bank B Reports: Status 11 (Current), Date Opened (Original Note Date), and a K2 Segment with Indicator 1 (Purchased From) and Bank A’s name.
Result: The credit report shows a continuous history rather than a jagged "Closed / New Account" pattern.9
7.3 K3 Segment: Mortgage Information
Standard for Portfolio Type M. It includes the Mortgage Identification Number (MIN), which links the loan to the MERS (Mortgage Electronic Registration Systems) database. This allows for tracking ownership in the complex secondary mortgage market.5
7.4 K4 Segment: Specialized Payment Info
This segment has gained prominence with the rise of "Buy Now Pay Later" and complex student loan deferments.
Fields: Deferred Payment Start Date, Balloon Payment Due Date, Balloon Payment Amount.
Usage: Allows a lender to report an account as "Current" even if the "Scheduled Payment Amount" is zero due to a deferment.5
8. Common Validation Errors and Rejection Logic
The snippets provided 28 highlight specific "Reject" codes (e.g., Error B1, B2). These represent the enforcement of Metro 2® logic by the receiving systems.
Error B1/B2 (Reject): Often indicates a mismatch between the Header Record identifiers and the Base Segment data, or an account that cannot be matched to an existing file.
Logical Rejections:
Date Logic: Reporting a Date of Last Payment that is future-dated relative to the Activity Date.
Status/Balance Mismatch: Reporting Status 13 (Paid) with a Balance of $50.
Grid/Status Mismatch: Reporting Status 11 (Current) but the first byte of the Payment History Grid is 1 (30 days late).
9. Conclusion: The Imperative of Precision
The Metro 2® format is a rigorous, logic-driven standard. It does not tolerate ambiguity. For the data furnisher, the task is not simply "reporting the data"; it is translating internal operational reality into the standardized lexicon of Metro 2®.
Current is not just a state of mind; it is Code 11 with zero Amount Past Due.
Dispute is not just a customer service note; it is Code XB mandated by federal law.
Bankruptcy is not just a loss; it is a specific sequence of Codes (A -> E) that mandates a zero balance upon discharge.
Understanding the specific codes for Portfolio Types (C/I/M/R/O), Account Types (00-99), Status Codes (11-97), and Special Comments allows the furnisher to construct a credit file that is accurate, compliant, and defensible. The tables and logic detailed in this report provide the blueprint for achieving that standard.
Table of Key Reference Codes
Category
Code
Meaning
Context
Portfolio
R
Revolving
Credit Cards
Portfolio
I
Installment
Auto/Student Loans
Status
11
Current
Good Standing
Status
97
Charge-off
Bad Debt (Unpaid)
Status
64
Paid Charge-off
Bad Debt (Paid)
Compliance
XB
Dispute (FCRA)
Consumer disagrees with data
Compliance
XA
Closed by Consumer
Voluntary closure
Comment
AW
Natural Disaster
Suppression of negatives
ECOA
1
Individual
Sole Liability
ECOA
2
Joint
Shared Liability
ECOA
3
Authorized User
No Liability

Works cited
Metro 2® Format for Credit Reporting - CDIA - Consumer Data Industry Association, accessed December 6, 2025, https://www.cdiaonline.org/resources/furnishers-of-data-overview/metro2-information/
Publications - CDIA - Consumer Data Industry Association, accessed December 6, 2025, https://www.cdiaonline.org/publications/
Data Reporting FAQs - TransUnion, accessed December 6, 2025, https://www.transunion.com/data-reporting/data-reporting-faqs
File structure | Moov Metro2, accessed December 6, 2025, https://moov-io.github.io/metro2/file-structure/
2020 Credit Reporting Resource Guide®, accessed December 6, 2025, http://autodealerplus.com/dealerzone/metro2.pdf
Metro 2 Format - Base Segment - Debt Collection Software, accessed December 6, 2025, https://www.collect.org/cv11/Help/metro2formatbasesegment.html
METRO 2 File Information, accessed December 6, 2025, https://secure.fidelityifs.com/bookshelf/bancpac/BancPac50/BP50/c_metro_2_file_information.html
Appendix 1 Credit Bureau Report Key Account Status Codes - Fiscal.Treasury.gov, accessed December 6, 2025, https://fiscal.treasury.gov/files/debt-management/appendix-1.pdf
Credit Reporting Guide - GOLDPoint Systems, accessed December 6, 2025, https://secure.goldpointsystems.com/gpsdocs/loans/CreditReporting/CreditReporting.pdf
Metro 2® Format: A Practical Overview - Metro2 Credit Reporting Software - Switch Labs, accessed December 6, 2025, https://metro2.switchlabs.dev/metro2/metro2-format-overview
Metro II Data Preparation & Reporting, accessed December 6, 2025, https://docs.oracle.com/en/industries/financial-services/financial-lending-leasing/14.12.0.0.0/metro-ii-data-preparation-and-reporting/metro-ii-data-preparation-and-reporting.pdf
How To Read The Metro2 Format - Collect! Help, accessed December 6, 2025, https://www.collect.org/cv12/Help/howtoreadthemetro2format.html
Metro Contact Description Codes - Debt Collection Software, accessed December 6, 2025, https://www.collect.org/cv11/Help/metrocontactdescriptioncodes.html
Credit Bureau Account Type Codes, accessed December 6, 2025, https://help.cubase.org/cubase/crdtbureauaccttypecodes.htm
Setting Account Status Codes, Payment Ratings, and Delinquency Dates for the Metro 2 format, accessed December 6, 2025, https://www.advancedlease.com/media/downloads/Metro2statuscodes.pdf
ECOA Codes - Credit Bureau Reporting Console - Genesys, accessed December 6, 2025, https://help.genesys.com/latitude/10/mergedProjects/CBRConsole/desktop/ecoa_codes.htm
ECOA Codes, accessed December 6, 2025, https://help.cubase.org/cubase/ecoacodes.htm
Appendix : Handling Metro II Account Statuses - Oracle Help Center, accessed December 6, 2025, https://docs.oracle.com/en/industries/financial-services/financial-lending-leasing/14.12.0.0.0/metro-ii-data-preparation-and-reporting/appendix-handling-metro-ii-account-statuses.html
Credit Bureau Status Codes, accessed December 6, 2025, https://help.cubase.org/cubase/crtburstatuscodes.htm
Metro 2 data mapping - LoanPro Knowledge Base, accessed December 6, 2025, https://help.loanpro.io/en_US/credit-reporting-options/metro-2-data-mapping
metro2/pkg/lib/base_segment.go at master - GitHub, accessed December 6, 2025, https://github.com/moov-io/metro2/blob/master/pkg/lib/base_segment.go
Credit Bureau Reporting Console - Compliance Condition Codes - Genesys, accessed December 6, 2025, https://help.genesys.com/latitude/10/mergedProjects/CBRConsole/desktop/compliance_condition_codes.htm
Credit Bureau Consumer Codes, accessed December 6, 2025, https://help.cubase.org/cubase/crdtburcodes.htm
Metro 2 Code Settings, accessed December 6, 2025, https://support.storis.com/helpRevisions/StorisWebHelp97/Settings/Actions_and_Field_Details/Metro_2_Code_Settings.htm
Credit Bureau Reporting Console - Special Comment Codes - Genesys, accessed December 6, 2025, https://help.genesys.com/latitude/10/mergedProjects/CBRConsole/desktop/special_comment_codes.htm
Credit Bureau Comment Codes, accessed December 6, 2025, https://help.cubase.org/cubase/crdtburcommentcodes.htm
Metro II Data Preparation & Reporting, accessed December 6, 2025, https://docs.oracle.com/en/industries/financial-services/financial-lending-leasing/15.0.0.0.0/metii/metro-ii-data-preparation-and-reporting.pdf
CIMOR Batch Provider Error Codes - Missouri Department of Mental Health, accessed December 6, 2025, https://dmh.mo.gov/themes/custom/labor/labor_2020/mo-viewer/viewer.html?file=https%3A%2F%2Fdmh.mo.gov%2Fsites%2Fdmh%2Ffiles%2Fmedia%2Fpdf%2F2024%2F04%2Fcimor-batch-provider-error-codes_0.pdf
cimor-batch-provider-error-codes_0.pdf, accessed December 6, 2025, https://dmh.mo.gov/themes/custom/labor/labor_2020/mo-viewer/viewer.html?file=https%3A%2F%2Fdmh.mo.gov%2Fsites%2Fdmh%2Ffiles%2Fmedia%2Fpdf%2F2024%2F12%2Fcimor-batch-provider-error-codes_0.pdf
