"""
edgar_client.py — Reusable EDGAR API client.

Usage:
    from scripts.edgar_client import EdgarClient
    client = EdgarClient("ResearchBot research@example.com")
    cik = client.ticker_to_cik("PLTR")
    snapshot = client.research_snapshot("PLTR")
"""

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
            extra = self._get(f"{self.BASE}/submissions/{f['name']}")
            df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
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

    def get_fact_series(self, cik: str, tag: str, taxonomy: str = "us-gaap",
                        unit: str = "USD", form_filter: str = "10-K") -> pd.DataFrame:
        facts = self._get_facts(cik)
        try:
            entries = facts[taxonomy][tag]["units"][unit]
        except KeyError:
            return pd.DataFrame(columns=["end", "val", "filed", "accn"])
        df = pd.DataFrame(entries)
        if form_filter:
            df = df[df["form"] == form_filter]
        df["end"] = pd.to_datetime(df["end"])
        df = df.sort_values("filed").drop_duplicates(subset=["end"], keep="last")
        return df[["end", "val", "filed", "accn"]].sort_values("end").reset_index(drop=True)

    def search(self, query: str, form: str = "10-K",
               start: str = None, end: str = None) -> list[dict]:
        params = {"q": f'"{query}"', "forms": form}
        if start: params["startdt"] = start
        if end: params["enddt"] = end
        data = self._get(self.EFTS, params=params)
        return data.get("hits", {}).get("hits", [])

    def research_snapshot(self, ticker: str) -> dict:
        cik = self.ticker_to_cik(ticker)
        filings = self.get_filings(cik, forms=["10-K", "10-Q"])
        k = filings[filings["form"] == "10-K"]
        q = filings[filings["form"] == "10-Q"]
        revenue = self.get_fact_series(cik, "Revenues")
        if revenue.empty:
            revenue = self.get_fact_series(cik, "RevenueFromContractWithCustomerExcludingAssessedTax")
        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "latest_10k_url": self.get_filing_url(cik, k.iloc[0]["accessionNumber"], k.iloc[0]["primaryDocument"]) if not k.empty else None,
            "latest_10q_url": self.get_filing_url(cik, q.iloc[0]["accessionNumber"], q.iloc[0]["primaryDocument"]) if not q.empty else None,
            "annual_revenue": revenue[["end", "val"]].to_dict("records"),
            "annual_net_income": self.get_fact_series(cik, "NetIncomeLoss")[["end", "val"]].to_dict("records"),
            "annual_operating_cf": self.get_fact_series(cik, "NetCashProvidedByUsedInOperatingActivities")[["end", "val"]].to_dict("records"),
        }
