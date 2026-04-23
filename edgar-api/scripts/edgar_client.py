"""
edgar_client.py — Reusable EDGAR API client.

Usage:
    from scripts.edgar_client import EdgarClient
    client = EdgarClient("ResearchBot research@example.com")
    cik = client.ticker_to_cik("PLTR")
    snapshot = client.research_snapshot("PLTR")
"""

import math
import time
import requests
import pandas as pd
from typing import Optional


class EdgarClient:
    BASE = "https://data.sec.gov"
    EFTS = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self, user_agent: str):
        self.headers = {"User-Agent": user_agent}
        self._ticker_map: Optional[dict] = None
        self._facts_cache: dict = {}

    def _get(self, url: str, params: dict = None) -> dict:
        time.sleep(0.11)
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    def _load_tickers(self):
        if self._ticker_map is None:
            data = self._get("https://www.sec.gov/files/company_tickers.json")
            self._ticker_map = {
                v["ticker"].upper(): str(v["cik_str"]).zfill(10)
                for v in data.values()
            }

    def ticker_to_cik(self, ticker: str) -> str:
        self._load_tickers()
        cik = self._ticker_map.get(ticker.upper())
        if not cik:
            raise ValueError(f"Ticker '{ticker}' not found")
        return cik

    def get_filings(self, cik: str, forms: list[str] = None) -> pd.DataFrame:
        data = self._get(f"{self.BASE}/submissions/CIK{cik}.json")
        df = pd.DataFrame(data["filings"]["recent"])
        for f in data["filings"].get("files", []):
            extra = pd.DataFrame(self._get(f"{self.BASE}/submissions/{f['name']}"))
            if not extra.empty:
                common_cols = df.columns.intersection(extra.columns)
                df = pd.concat(
                    [df[common_cols].dropna(axis=1, how="all"),
                     extra[common_cols].dropna(axis=1, how="all")],
                    ignore_index=True,
                )
        if forms:
            df = df[df["form"].isin(forms)]
        df["filingDate"] = pd.to_datetime(df["filingDate"])
        return df.sort_values("filingDate", ascending=False).reset_index(drop=True)

    def get_filing_url(self, cik: str, accession_number: str, primary_doc: str) -> str:
        acc_clean = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{primary_doc}"

    def _get_facts(self, cik: str) -> dict:
        if cik not in self._facts_cache:
            self._facts_cache[cik] = self._get(f"{self.BASE}/api/xbrl/companyfacts/CIK{cik}.json")
        return self._facts_cache[cik]

    def _get_gaap(self, cik: str) -> dict:
        # Facts are nested under ["facts"]["us-gaap"], not at the top level
        return self._get_facts(cik)["facts"].get("us-gaap", {})

    def get_fact_series(self, cik: str, tag: str, taxonomy: str = "us-gaap",
                        unit: str = "USD", form_filter: str = "10-K",
                        annual_only: bool = True) -> pd.DataFrame:
        """
        annual_only: filter income/CF entries to ~365-day periods to exclude
                     quarterly cumulative values also tagged 10-K.
                     Set False for balance sheet items (no 'start' field).
        """
        gaap = self._get_facts(cik)["facts"].get(taxonomy, {})
        if tag not in gaap:
            return pd.DataFrame(columns=["end", "val", "filed"])
        units = gaap[tag].get("units", {})
        # Fall back to CAD for Canadian 40-F filers
        entries = units.get(unit, units.get("CAD", []))
        if not entries:
            return pd.DataFrame(columns=["end", "val", "filed"])
        df = pd.DataFrame(entries)
        if form_filter:
            df = df[df["form"] == form_filter].copy()
        if df.empty:
            return pd.DataFrame(columns=["end", "val", "filed"])
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
        cols = [c for c in ["end", "val", "filed", "accn", "start"] if c in df.columns]
        return df[cols].sort_values("end").reset_index(drop=True)

    def search(self, query: str, form: str = "10-K",
               start: str = None, end: str = None) -> list[dict]:
        params = {"q": f'"{query}"', "forms": form}
        if start: params["startdt"] = start
        if end: params["enddt"] = end
        data = self._get(self.EFTS, params=params)
        return data.get("hits", {}).get("hits", [])

    def get_fact_with_fallbacks(self, cik: str, tags: list[str], **kwargs) -> pd.DataFrame:
        """Try each tag, return the one with the most recent data."""
        best = pd.DataFrame(columns=["end", "val", "filed"])
        best_max_date = pd.Timestamp.min
        for tag in tags:
            result = self.get_fact_series(cik, tag, **kwargs)
            if not result.empty:
                max_date = result["end"].max()
                if max_date > best_max_date:
                    best = result
                    best_max_date = max_date
        return best

    def _latest_val(self, records: list[dict]) -> float:
        """Get the latest value from a list of {end, val} records."""
        if not records:
            return float("nan")
        return records[-1]["val"]

    def _latest_year(self, records: list[dict]) -> int:
        """Get the year from the latest record."""
        if not records:
            return 0
        end = records[-1]["end"]
        return end.year if hasattr(end, "year") else int(str(end)[:4])

    def export_snapshot_csv(self, tickers: list[str],
                            output_path: str = None) -> pd.DataFrame:
        """Export a wide-format CSV with latest-year financials per ticker.

        Values are in $M rounded to 1 decimal. Returns the DataFrame
        and optionally writes to output_path.
        """
        rows = []
        for ticker in tickers:
            try:
                snap = self.research_snapshot(ticker)
                cik = snap["cik"]
                ebit_series = self.get_fact_with_fallbacks(
                    cik, ["OperatingIncomeLoss"]
                )
                rev = self._latest_val(snap["annual_revenue"])
                ni = self._latest_val(snap["annual_net_income"])
                cfo = self._latest_val(snap["annual_operating_cf"])
                cash = self._latest_val(snap["cash"])
                debt = self._latest_val(snap["long_term_debt"])
                ebit = ebit_series["val"].iloc[-1] if not ebit_series.empty else float("nan")
                # Revenue growth YoY
                rev_list = snap["annual_revenue"]
                if len(rev_list) >= 2:
                    prev = rev_list[-2]["val"]
                    growth = (rev - prev) / abs(prev) if prev != 0 else float("nan")
                else:
                    growth = float("nan")
                rows.append({
                    "ticker": ticker.upper(),
                    "latest_year": self._latest_year(snap["annual_revenue"]),
                    "revenue_m": round(rev / 1e6, 1) if not math.isnan(rev) else None,
                    "net_income_m": round(ni / 1e6, 1) if not math.isnan(ni) else None,
                    "ebit_m": round(ebit / 1e6, 1) if not math.isnan(ebit) else None,
                    "ebit_margin": round(ebit / rev, 3) if not (math.isnan(ebit) or math.isnan(rev) or rev == 0) else None,
                    "operating_cf_m": round(cfo / 1e6, 1) if not math.isnan(cfo) else None,
                    "cash_m": round(cash / 1e6, 1) if not math.isnan(cash) else None,
                    "long_term_debt_m": round(debt / 1e6, 1) if not math.isnan(debt) else None,
                    "net_debt_m": round((debt - cash) / 1e6, 1) if not (math.isnan(debt) or math.isnan(cash)) else None,
                    "rev_growth_yoy": round(growth, 3) if not math.isnan(growth) else None,
                })
            except Exception as e:
                print(f"Warning: {ticker} failed: {e}")
                rows.append({"ticker": ticker.upper()})
        df = pd.DataFrame(rows)
        if output_path:
            df.to_csv(output_path, index=False)
            print(f"Wrote {len(df)} rows to {output_path}")
        return df

    def export_timeseries_csv(self, tickers: list[str],
                               output_path: str = None) -> pd.DataFrame:
        """Export a long-format CSV with multi-year financials per ticker.

        Columns: ticker, year, metric, value_m. Values in $M.
        Returns the DataFrame and optionally writes to output_path.
        """
        ts_rows = []
        for ticker in tickers:
            try:
                snap = self.research_snapshot(ticker)
                cik = snap["cik"]
                ebit_series = self.get_fact_with_fallbacks(
                    cik, ["OperatingIncomeLoss"]
                )
                series_map = {
                    "revenue": snap["annual_revenue"],
                    "net_income": snap["annual_net_income"],
                    "operating_cf": snap["annual_operating_cf"],
                    "cash": snap["cash"],
                    "long_term_debt": snap["long_term_debt"],
                }
                for metric, records in series_map.items():
                    for r in records:
                        end = r["end"]
                        year = end.year if hasattr(end, "year") else int(str(end)[:4])
                        ts_rows.append({
                            "ticker": ticker.upper(),
                            "year": year,
                            "metric": metric,
                            "value_m": round(r["val"] / 1e6, 1),
                        })
                if not ebit_series.empty:
                    for _, row in ebit_series.iterrows():
                        ts_rows.append({
                            "ticker": ticker.upper(),
                            "year": row["end"].year,
                            "metric": "ebit",
                            "value_m": round(row["val"] / 1e6, 1),
                        })
            except Exception as e:
                print(f"Warning: {ticker} timeseries failed: {e}")
        df = pd.DataFrame(ts_rows)
        if output_path:
            df.to_csv(output_path, index=False)
            print(f"Wrote {len(df)} rows to {output_path}")
        return df

    def research_snapshot(self, ticker: str) -> dict:
        cik = self.ticker_to_cik(ticker)
        filings = self.get_filings(cik, forms=["10-K", "10-Q"])
        k = filings[filings["form"] == "10-K"]
        q = filings[filings["form"] == "10-Q"]
        revenue = self.get_fact_with_fallbacks(cik, [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ])
        net_income = self.get_fact_with_fallbacks(cik, ["NetIncomeLoss", "ProfitLoss"])
        operating_cf = self.get_fact_with_fallbacks(cik, [
            "NetCashProvidedByUsedInOperatingActivities",
        ])
        cash = self.get_fact_with_fallbacks(cik, [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            "CashCashEquivalentsAndShortTermInvestments",
        ], annual_only=False)
        debt = self.get_fact_with_fallbacks(cik, [
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "LongTermDebtAndCapitalLeaseObligations",
        ], annual_only=False)
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "latest_10k_url": self.get_filing_url(cik, k.iloc[0]["accessionNumber"], k.iloc[0]["primaryDocument"]) if not k.empty else None,
            "latest_10q_url": self.get_filing_url(cik, q.iloc[0]["accessionNumber"], q.iloc[0]["primaryDocument"]) if not q.empty else None,
            "annual_revenue": revenue[["end", "val"]].to_dict("records"),
            "annual_net_income": net_income[["end", "val"]].to_dict("records"),
            "annual_operating_cf": operating_cf[["end", "val"]].to_dict("records"),
            "cash": cash[["end", "val"]].tail(4).to_dict("records"),
            "long_term_debt": debt[["end", "val"]].tail(4).to_dict("records"),
        }
