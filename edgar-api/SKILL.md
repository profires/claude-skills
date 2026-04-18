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

def get_fact_series(facts: dict, tag: str, form_filter: str = "10-K") -> pd.DataFrame:
    try:
        entries = facts["us-gaap"][tag]["units"]["USD"]
    except KeyError:
        return pd.DataFrame()
    df = pd.DataFrame(entries)
    df = df[df["form"] == form_filter].copy()
    df["end"] = pd.to_datetime(df["end"])
    df = df.sort_values("filed").drop_duplicates(subset=["end"], keep="last")
    return df[["end", "val", "filed", "accn"]].sort_values("end")

revenue = get_fact_series(facts, "Revenues")
# If empty, try: get_fact_series(facts, "RevenueFromContractWithCustomerExcludingAssessedTax")
```

### 5. Single Concept (Faster)

```python
r = requests.get(
    f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/NetIncomeLoss.json",
    headers=headers,
)
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

## Common XBRL Tags

See `references/xbrl-tags.md` for the full list with aliases.

**Income:** Revenues, NetIncomeLoss, OperatingIncomeLoss, GrossProfit, EarningsPerShareDiluted
**Balance sheet:** Assets, Liabilities, StockholdersEquity, CashAndCashEquivalentsAtCarryingValue, LongTermDebt
**Cash flow:** NetCashProvidedByUsedInOperatingActivities, PaymentsToAcquirePropertyPlantAndEquipment

## Gotchas

- **CIK must be 10 digits** — always `str(cik).zfill(10)`
- **Accession number in URLs** — strip hyphens: `0001234567-24-000001` → `000123456724000001`
- **Duplicate XBRL values** — deduplicate by keeping latest filed per period end
- **Tag aliases** — PLTR uses `RevenueFromContractWithCustomerExcludingAssessedTax`, not `Revenues`
- **Non-US filers** — use `ifrs-full` taxonomy instead of `us-gaap` for 20-F filers
- **SET/Thai stocks** — EDGAR doesn't cover them; see `references/set-api.md`

## Reference Files

- `references/xbrl-tags.md` — full tag list with aliases, units, period types
- `references/set-api.md` — SET Thailand disclosure API
- `scripts/edgar_client.py` — reusable Python client class; copy to working dir before use
