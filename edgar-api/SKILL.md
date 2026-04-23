---
name: edgar-api
description: >
  Pull financial filings and structured data from the SEC EDGAR API. Use this skill
  whenever the user wants to fetch 10-K, 10-Q, 8-K or any SEC filing for a company,
  look up a company's CIK, extract XBRL financial facts (revenue, assets, EPS, etc.),
  retrieve filing history, or download actual filing documents. Trigger on phrases like
  "get the 10-K for...", "pull SEC filings", "EDGAR data for...", "fetch financials from
  SEC", "company facts EDGAR", "filing history", "XBRL data", or any mention of SEC
  disclosure retrieval. Always use this skill before writing any EDGAR-related code.
---

# EDGAR API Skill

SEC EDGAR's public REST API at `data.sec.gov` — no API key required, just a User-Agent header.

## Quick Reference

| Goal | Endpoint |
|------|----------|
| Lookup CIK by ticker | `https://www.sec.gov/files/company_tickers.json` |
| Filing history | `https://data.sec.gov/submissions/CIK{10-digit-cik}.json` |
| All XBRL facts | `https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit-cik}.json` |
| One concept | `https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json` |
| Full-text search | `https://efts.sec.gov/LATEST/search-index?q="{query}"&forms={form}` |

## Rate Limiting & Headers

**Required header on every request:**

```
User-Agent: YourAppName <contact@email.com>
```

SEC will block requests without this. Rate limit: 10 req/s max — add `time.sleep(0.1)` between calls.

---

## Step-by-Step Workflows

### 1. Ticker → CIK

```python
import requests

headers = {"User-Agent": "ResearchBot research@example.com"}
r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
tickers = r.json()

def ticker_to_cik(ticker: str) -> str:
    for entry in tickers.values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)  # must be 10 digits
    raise ValueError(f"Ticker {ticker} not found")

cik = ticker_to_cik("PLTR")  # → "0001321655"
```

### 2. Filing History

```python
import pandas as pd

r = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers)
data = r.json()
df = pd.DataFrame(data["filings"]["recent"])

# Handle companies with >1000 filings
for f in data["filings"].get("files", []):
    extra = requests.get(f"https://data.sec.gov/submissions/{f['name']}", headers=headers).json()
    df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)

annual = df[df["form"].isin(["10-K", "10-Q"])].sort_values("filingDate", ascending=False)
```

### 3. Fetch Actual Filing Document

```python
def get_filing_url(cik: str, accession_number: str, primary_doc: str) -> str:
    acc_clean = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{primary_doc}"

row = annual[annual["form"] == "10-K"].iloc[0]
url = get_filing_url(cik, row["accessionNumber"], row["primaryDocument"])
```

### 4. XBRL Company Facts (Structured Financials)

```python
r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=headers)
facts = r.json()

# ⚠️ Facts are nested under facts["facts"], not facts directly
gaap = facts["facts"].get("us-gaap", {})

def get_fact_series(gaap: dict, tag: str, form_filter: str = "10-K",
                    annual_only: bool = True) -> pd.DataFrame:
    """
    annual_only: filter to ~365-day periods (income/CF items only).
                 Set False for balance sheet items (no 'start' field).
    """
    if tag not in gaap:
        return pd.DataFrame()
    units = gaap[tag].get("units", {})
    entries = units.get("USD", units.get("CAD", []))  # fallback for Canadian filers
    if not entries:
        return pd.DataFrame()
    df = pd.DataFrame(entries)
    if form_filter:
        df = df[df["form"] == form_filter].copy()
    if df.empty:
        return pd.DataFrame()
    df["end"] = pd.to_datetime(df["end"])
    if "start" in df.columns:
        df["start"] = pd.to_datetime(df["start"])
        # Dedup on (end, start) so a stand-alone quarter and a YTD cumulative
        # sharing the same end date both survive for the period-length filter.
        dedup_keys = ["end", "start"]
    else:
        dedup_keys = ["end"]
    df = df.sort_values("filed").drop_duplicates(subset=dedup_keys, keep="last")
    if annual_only and "start" in df.columns and df["start"].notna().any():
        df["days"] = (df["end"] - df["start"]).dt.days
        df = df[df["days"].between(340, 380)]
    cols = [c for c in ["end", "val", "filed", "start"] if c in df.columns]
    return df[cols].sort_values("end").reset_index(drop=True)

# Revenue: try post-ASC 606 tag first, then legacy fallback
revenue = get_fact_series(gaap, "RevenueFromContractWithCustomerExcludingAssessedTax")
if revenue.empty:
    revenue = get_fact_series(gaap, "Revenues")

# Balance sheet (no start field — set annual_only=False)
cash = get_fact_series(gaap, "CashAndCashEquivalentsAtCarryingValue", annual_only=False)
```

### 5. Single Concept (Faster)

```python
r = requests.get(
    f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/NetIncomeLoss.json",
    headers=headers,
)
# companyconcept endpoint returns units directly (no "facts" wrapper)
entries = r.json()["units"]["USD"]
```

### 6. Full-Text Search

```python
def edgar_search(query: str, form: str = "10-K", start: str = None, end: str = None):
    params = {"q": f'"{query}"', "forms": form}
    if start: params["startdt"] = start
    if end: params["enddt"] = end
    r = requests.get("https://efts.sec.gov/LATEST/search-index", params=params, headers=headers)
    return r.json().get("hits", {}).get("hits", [])
```

### 7. CSV Export (Batch Financials)

```python
client = EdgarClient("ResearchBot research@example.com")

# Wide format: one row per ticker with latest-year financials ($M)
df = client.export_snapshot_csv(
    ["AAPL", "MSFT", "GOOGL"],
    output_path="snapshot.csv",  # optional — also returns DataFrame
)
# Columns: ticker, latest_year, revenue_m, net_income_m, ebit_m,
#   ebit_margin, operating_cf_m, cash_m, long_term_debt_m, net_debt_m, rev_growth_yoy

# Long format: multi-year time series for trend analysis
ts = client.export_timeseries_csv(
    ["AAPL", "MSFT", "GOOGL"],
    output_path="timeseries.csv",
)
# Columns: ticker, year, metric, value_m
# Metrics: revenue, net_income, ebit, operating_cf, cash, long_term_debt
```

## Common XBRL Tags

See `references/xbrl-tags.md` for the full list with aliases.

**Income:** NetIncomeLoss (fallback: ProfitLoss), Revenues, OperatingIncomeLoss, GrossProfit, EarningsPerShareDiluted
**Balance sheet:** Assets, Liabilities, StockholdersEquity, CashAndCashEquivalentsAtCarryingValue, LongTermDebt
**Cash flow:** NetCashProvidedByUsedInOperatingActivities, PaymentsToAcquirePropertyPlantAndEquipment

## Gotchas

- **Facts are nested** — response is `facts["facts"]["us-gaap"]`, NOT `facts["us-gaap"]`
- **CIK must be 10 digits** — always `str(cik).zfill(10)`
- **Accession number in URLs** — strip hyphens: `0001234567-24-000001` → `000123456724000001`
- **Duplicate XBRL values** — deduplicate by keeping latest filed per period end
- **Revenue tag priority** — try `RevenueFromContractWithCustomerExcludingAssessedTax` FIRST (post-ASC 606, 2018+); `Revenues` often only has pre-2018 data and will return stale decade-old figures
- **Annual period filtering** — income/CF entries include quarterly cumulative values also tagged `10-K`; filter to `days between 340–380` to get true annual figures
- **Balance sheet items have no `start` field** — `Assets`, `CashAndCashEquivalentsAtCarryingValue`, `LongTermDebt` etc. are point-in-time; don't apply period-length filter or they'll all drop
- **20-F filers** — foreign private issuers (non-Canadian) use `ifrs-full` taxonomy instead of `us-gaap`
- **40-F filers** — Canadian companies (e.g. Cameco/CCJ, Shopify/SHOP) file 40-F under Canadian GAAP; `us-gaap` will be empty. Use manual data or check `ifrs-full`
- **Net income tag varies** — some companies (e.g. Bloom Energy/BE) use `ProfitLoss` instead of `NetIncomeLoss` for recent filings; always try both with fallback
- **companyconcept endpoint** — returns `r.json()["units"]["USD"]` directly, no `"facts"` wrapper
- **SET/Thai stocks** — EDGAR doesn't cover them; see `references/set-api.md`

## Reference Files

- `references/xbrl-tags.md` — full tag list with aliases, units, period types
- `references/set-api.md` — SET Thailand disclosure API
- `scripts/edgar_client.py` — reusable Python client class; copy to working dir before use
