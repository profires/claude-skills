# SET (Stock Exchange of Thailand) Disclosure API

EDGAR does not cover Thai-listed companies. Use these alternatives.

## SEC Thailand OpenAPI

- Portal: https://openapi.sec.or.th
- Registration required for higher rate limits; free tier available

### Key Endpoints

```
GET https://openapi.sec.or.th/fin-stat/1.0.0/company/profile?symbol={SYMBOL}
GET https://openapi.sec.or.th/fin-stat/1.0.0/financial-statement?symbol={SYMBOL}&period={YYYYQ}
```

## yfinance Workaround (Quick & Dirty)

```python
import yfinance as yf

ticker = yf.Ticker("PTT.BK")   # append .BK for SET stocks
financials = ticker.financials          # annual income statement
quarterly = ticker.quarterly_financials
balance = ticker.balance_sheet
cashflow = ticker.cashflow
```

Note: yfinance/Yahoo Finance may lag for Thai stocks. Use SEC Thailand API for authoritative data.

## Filing Types

- Annual: **56-1 One Report** (since 2021, merged disclosure + annual report)
- Quarterly: **FS filings** (งบการเงิน)
- Standard: TFRS (Thai Financial Reporting Standards) ≈ IFRS
