# XBRL Tag Reference — us-gaap Taxonomy

## Income Statement

> **Tag priority for revenue:** Try `RevenueFromContractWithCustomerExcludingAssessedTax` first
> (post-ASC 606, 2018+). `Revenues` often only has pre-2018 data and returns stale figures.

| Concept | Primary Tag (try first) | Alternate Tags |
|---------|------------------------|----------------|
| Revenue | `RevenueFromContractWithCustomerExcludingAssessedTax` | `RevenueFromContractWithCustomerIncludingAssessedTax`, `Revenues`, `SalesRevenueNet`, `ContractsRevenue` |
| Gross Profit | `GrossProfit` | — |
| R&D | `ResearchAndDevelopmentExpense` | — |
| SG&A | `SellingGeneralAndAdministrativeExpense` | `GeneralAndAdministrativeExpense` |
| Operating Income | `OperatingIncomeLoss` | — |
| Net Income | `NetIncomeLoss` | `ProfitLoss` (some companies use this exclusively for recent filings) |
| EPS Basic | `EarningsPerShareBasic` | — |
| EPS Diluted | `EarningsPerShareDiluted` | — |
| Shares (basic) | `WeightedAverageNumberOfSharesOutstandingBasic` | — |
| Shares (diluted) | `WeightedAverageNumberOfDilutedSharesOutstanding` | — |

## Balance Sheet

> **Balance sheet items have no `start` field** — they are point-in-time snapshots.
> Always pass `annual_only=False` when fetching these or the period-length filter will drop all rows.

| Concept | Primary Tag | Alternate Tags |
|---------|------------|----------------|
| Total Assets | `Assets` | — |
| Current Assets | `AssetsCurrent` | — |
| Cash | `CashAndCashEquivalentsAtCarryingValue` | `CashCashEquivalentsAndShortTermInvestments`, `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` |
| Accounts Receivable | `AccountsReceivableNetCurrent` | `ReceivablesNetCurrent` |
| Total Liabilities | `Liabilities` | — |
| Long-Term Debt | `LongTermDebt` | `LongTermDebtNoncurrent`, `LongTermDebtAndCapitalLeaseObligations` |
| Total Equity | `StockholdersEquity` | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| Shares Outstanding | `CommonStockSharesOutstanding` | — |

## Cash Flow

| Concept | Primary Tag | Alternate Tags |
|---------|------------|----------------|
| Operating CF | `NetCashProvidedByUsedInOperatingActivities` | — |
| Investing CF | `NetCashProvidedByUsedInInvestingActivities` | — |
| Financing CF | `NetCashProvidedByUsedInFinancingActivities` | — |
| CapEx | `PaymentsToAcquirePropertyPlantAndEquipment` | `CapitalExpendituresIncurredButNotYetPaid`, `PaymentsToAcquireProductiveAssets` |
| D&A | `DepreciationDepletionAndAmortization` | `DepreciationAndAmortization` |
| Stock-based comp | `ShareBasedCompensation` | `AllocatedShareBasedCompensationExpense` |

## Units by Type

- Financial values → `USD`
- Share counts → `shares`
- Per-share → `USD/shares`
- Ratios → `pure`

## Period Types

- Balance sheet items: instantaneous facts (no `start` field, only `end`)
- Income/CF items: duration facts (both `start` and `end` present)
