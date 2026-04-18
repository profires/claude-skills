# XBRL Tag Reference — us-gaap Taxonomy

## Income Statement

| Concept | Primary Tag | Alternate Tags |
|---------|------------|----------------|
| Revenue | `Revenues` | `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` |
| Gross Profit | `GrossProfit` | — |
| R&D | `ResearchAndDevelopmentExpense` | — |
| SG&A | `SellingGeneralAndAdministrativeExpense` | `GeneralAndAdministrativeExpense` |
| Operating Income | `OperatingIncomeLoss` | — |
| Net Income | `NetIncomeLoss` | `ProfitLoss` |
| EPS Basic | `EarningsPerShareBasic` | — |
| EPS Diluted | `EarningsPerShareDiluted` | — |
| Shares (basic) | `WeightedAverageNumberOfSharesOutstandingBasic` | — |
| Shares (diluted) | `WeightedAverageNumberOfDilutedSharesOutstanding` | — |

## Balance Sheet

| Concept | Primary Tag | Alternate Tags |
|---------|------------|----------------|
| Total Assets | `Assets` | — |
| Current Assets | `AssetsCurrent` | — |
| Cash | `CashAndCashEquivalentsAtCarryingValue` | `CashCashEquivalentsAndShortTermInvestments` |
| Accounts Receivable | `AccountsReceivableNetCurrent` | `ReceivablesNetCurrent` |
| Total Liabilities | `Liabilities` | — |
| Long-Term Debt | `LongTermDebt` | `LongTermDebtNoncurrent` |
| Total Equity | `StockholdersEquity` | `StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` |
| Shares Outstanding | `CommonStockSharesOutstanding` | — |

## Cash Flow

| Concept | Primary Tag | Alternate Tags |
|---------|------------|----------------|
| Operating CF | `NetCashProvidedByUsedInOperatingActivities` | — |
| Investing CF | `NetCashProvidedByUsedInInvestingActivities` | — |
| Financing CF | `NetCashProvidedByUsedInFinancingActivities` | — |
| CapEx | `PaymentsToAcquirePropertyPlantAndEquipment` | — |
| D&A | `DepreciationDepletionAndAmortization` | `DepreciationAndAmortization` |
| Stock-based comp | `ShareBasedCompensation` | — |

## Units by Type

- Financial values → `USD`
- Share counts → `shares`
- Per-share → `USD/shares`
- Ratios → `pure`

## Period Types

- Balance sheet items: instantaneous facts (no `start` field, only `end`)
- Income/CF items: duration facts (both `start` and `end` present)
