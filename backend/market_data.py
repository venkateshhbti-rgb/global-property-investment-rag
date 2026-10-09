"""Live macro, house-price and currency data from open, keyless APIs.

Sources:
  - Open-Meteo geocoding  (market name -> country)
  - World Bank Open Data  (inflation, GDP growth, lending rate, population, migration)
  - BIS property prices   (nominal residential house-price growth, ~60 countries)
  - fawazahmed0 currency-api (FX rates and 12-month moves)
Results are cached on disk and refreshed at most once per day.
"""
import csv
import datetime as dt
import io
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import requests

from config import settings

CACHE_TTL = 24 * 3600
RETRY_AFTER = 600
TIMEOUT = 8
HEADERS = {"User-Agent": "property-rag-consultant/1.0"}

WB_INDICATORS = {
    "inflation": ("FP.CPI.TOTL.ZG", "Inflation (CPI)", "%"),
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "GDP growth", "%"),
    "lending_rate": ("FR.INR.LEND", "Lending interest rate", "%"),
    "population_growth": ("SP.POP.GROW", "Population growth", "%"),
    "net_migration": ("SM.POP.NETM", "Net migration (5-yr estimate)", "people"),
}

_EURO = "DE FR ES IT PT NL BE AT IE FI GR LU SK SI EE LV LT MT CY HR".split()
CURRENCY_BY_COUNTRY = {
    **{c: "EUR" for c in _EURO},
    "AE": "AED", "IN": "INR", "GB": "GBP", "US": "USD", "SG": "SGD", "SA": "SAR", "QA": "QAR",
    "KW": "KWD", "BH": "BHD", "OM": "OMR", "TR": "TRY", "EG": "EGP", "PK": "PKR", "BD": "BDT",
    "LK": "LKR", "NP": "NPR", "TH": "THB", "MY": "MYR", "ID": "IDR", "PH": "PHP", "VN": "VND",
    "HK": "HKD", "CN": "CNY", "JP": "JPY", "KR": "KRW", "TW": "TWD", "AU": "AUD", "NZ": "NZD",
    "CA": "CAD", "MX": "MXN", "BR": "BRL", "AR": "ARS", "CL": "CLP", "CO": "COP", "PE": "PEN",
    "ZA": "ZAR", "KE": "KES", "NG": "NGN", "MA": "MAD", "CH": "CHF", "SE": "SEK", "NO": "NOK",
    "DK": "DKK", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "RO": "RON", "BG": "BGN", "RU": "RUB",
    "UA": "UAH", "IL": "ILS", "JO": "JOD", "IS": "ISK", "MU": "MUR", "GE": "GEL", "KZ": "KZT",
}


def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def _first_ok(urls: List[str], attempts: int = 3) -> Optional[requests.Response]:
    for url in urls:
        for attempt in range(attempts):
            try:
                return _get(url)
            except requests.RequestException:
                time.sleep(0.8 * (attempt + 1))
    return None


def _fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def _fmt_people(v: float) -> str:
    sign = "+" if v >= 0 else "-"
    n = abs(v)
    if n >= 1_000_000:
        return f"{sign}{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{sign}{n / 1_000:.0f}k"
    return f"{sign}{n:.0f}"


class MarketData:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.RLock()
        self.data: Dict[str, Dict[str, Any]] = {}
        self._refreshing = False
        self._load()

    # ---------- persistence ----------
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (OSError, ValueError):
                self.data = {}

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
        os.replace(tmp, self.path)

    # ---------- fetchers ----------
    def _overrides(self) -> Dict[str, str]:
        path = os.path.join(settings.DATA_BASE_PATH, "_market_overrides.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {k.lower(): v.upper() for k, v in json.load(f).items()}
        except (OSError, ValueError):
            return {}

    def _geocode(self, region: str) -> Optional[Dict[str, str]]:
        code = self._overrides().get(region.lower())
        if code:
            return {"country_code": code, "country": code, "matched": f"{region} (override)"}
        resp = _first_ok([
            f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(region)}&count=1&format=json"
        ])
        results = (resp.json().get("results") if resp else None) or []
        if not results:
            return None
        r = results[0]
        return {"country_code": r["country_code"], "country": r.get("country", r["country_code"]),
                "matched": f"{r.get('name', region)}, {r.get('admin1', '')}".strip(", ")}

    @staticmethod
    def _world_bank(code: str, key: str) -> Optional[Dict[str, Any]]:
        indicator = WB_INDICATORS[key][0]
        resp = _first_ok([
            f"https://api.worldbank.org/v2/country/{code}/indicator/{indicator}?format=json&mrnev=1"
        ])
        try:
            row = resp.json()[1][0] if resp else None
        except (ValueError, IndexError, TypeError, KeyError):
            row = None
        if not row or row.get("value") is None:
            return None
        return {"value": float(row["value"]), "year": str(row["date"])}

    @staticmethod
    def _bis_house_prices(code: str) -> Optional[Dict[str, Any]]:
        try:
            resp = _get(f"https://stats.bis.org/api/v1/data/WS_SPP/Q.{code}.N.771?lastNObservations=1&format=csv")
            rows = list(csv.DictReader(io.StringIO(resp.text)))
            if rows and rows[-1].get("OBS_VALUE"):
                return {"yoy": float(rows[-1]["OBS_VALUE"]), "period": rows[-1]["TIME_PERIOD"]}
        except (requests.RequestException, ValueError, KeyError):
            pass
        return None

    @staticmethod
    def _fetch_fx() -> Optional[Dict[str, Any]]:
        latest = _first_ok([
            "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
            "https://latest.currency-api.pages.dev/v1/currencies/usd.json",
        ])
        if not latest:
            return None
        now = latest.json()
        wanted = set(c.lower() for c in CURRENCY_BY_COUNTRY.values())
        out = {"date": now.get("date"), "rates": {k: v for k, v in now["usd"].items() if k in wanted},
               "old_date": None, "old_rates": {}}
        year_ago = (dt.date.today() - dt.timedelta(days=365)).isoformat()
        old = _first_ok([
            f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{year_ago}/v1/currencies/usd.json",
            f"https://{year_ago}.currency-api.pages.dev/v1/currencies/usd.json",
        ])
        if old:
            body = old.json()
            out["old_date"] = body.get("date")
            out["old_rates"] = {k: v for k, v in body["usd"].items() if k in wanted}
        return out

    def _build(self, region: str, fx: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        record: Dict[str, Any] = {"region": region, "errors": [], "indicators": {}, "house_prices": None, "fx": None}
        place = self._geocode(region)
        if not place:
            record["errors"].append("Could not match this market to a country (add it to data/_market_overrides.json)")
            record["ok_at"] = 0
            record["fetched"] = time.time() - CACHE_TTL + RETRY_AFTER
            return record

        code = place["country_code"]
        record.update(place)
        currency = CURRENCY_BY_COUNTRY.get(code)
        record["currency"] = currency

        with ThreadPoolExecutor(max_workers=3) as ex:
            wb = {k: ex.submit(self._world_bank, code, k) for k in WB_INDICATORS}
            bis = ex.submit(self._bis_house_prices, code)
            for key, fut in wb.items():
                value = fut.result()
                if value:
                    record["indicators"][key] = value
            record["house_prices"] = bis.result()

        if fx and currency:
            cur = currency.lower()
            if currency == "USD":
                record["fx"] = {"rate": 1.0, "date": fx["date"], "change_12m_pct": 0.0}
            elif cur in fx["rates"]:
                rate, old = fx["rates"][cur], fx["old_rates"].get(cur)
                record["fx"] = {
                    "rate": rate, "date": fx["date"],
                    "change_12m_pct": round((old / rate - 1) * 100, 1) if old else None,
                }

        if not record["indicators"]:
            record["errors"].append("World Bank returned no indicators")
        ok = bool(record["indicators"])
        record["ok_at"] = time.time() if ok else 0
        record["fetched"] = time.time() if ok else time.time() - CACHE_TTL + RETRY_AFTER
        return record

    # ---------- refresh ----------
    def refresh(self, regions: List[str], force: bool = False):
        now = time.time()
        with self.lock:
            todo = [r for r in regions if force or r not in self.data or now - self.data[r].get("fetched", 0) > CACHE_TTL]
        if not todo:
            return
        fx = self._fetch_fx()
        with ThreadPoolExecutor(max_workers=2) as ex:
            built = list(ex.map(lambda r: self._build(r, fx), todo))
        with self.lock:
            for rec in built:
                self.data[rec["region"]] = rec
            self._save()

    def refresh_async(self, regions: List[str]):
        with self.lock:
            if self._refreshing:
                return
            self._refreshing = True

        def run():
            try:
                self.refresh(regions)
            except Exception as e:  # network trouble must never break the app
                print(f"[market-data] refresh failed: {e}")
            finally:
                with self.lock:
                    self._refreshing = False

        threading.Thread(target=run, daemon=True).start()

    # ---------- use ----------
    def stamp(self) -> str:
        """Changes when new live data arrives, so saved answers built on older data are not reused."""
        with self.lock:
            times = [r.get("ok_at", 0) for r in self.data.values()]
        return dt.datetime.utcfromtimestamp(max(times)).strftime("%Y-%m-%d") if times and max(times) else ""

    def snapshot(self, regions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        with self.lock:
            names = regions if regions is not None else sorted(self.data)
            return [self.data[r] for r in names if r in self.data]

    def _line(self, rec: Dict[str, Any]) -> str:
        """One labelled line per metric, with explicit gaps, so figures cannot be attributed to the wrong market."""
        name = rec["region"]
        ind = rec.get("indicators", {})
        if not ind and not rec.get("house_prices") and not rec.get("fx"):
            return ""
        lines = [f"[{name}] (national data for {rec.get('country', '?')}; currency {rec.get('currency') or 'unknown'})"]
        for key, (_, label, unit) in WB_INDICATORS.items():
            if key in ind:
                v = ind[key]["value"]
                text = _fmt_people(v) if unit == "people" else _fmt_pct(v)
                lines.append(f"{name} | {label}: {text} (World Bank, {ind[key]['year']})")
            else:
                lines.append(f"{name} | {label}: not available")
        hp = rec.get("house_prices")
        if hp:
            lines.append(f"{name} | House-price index, nominal y/y: {hp['yoy']:+.1f}% (BIS, {hp['period']})")
        else:
            lines.append(f"{name} | House-price index: not available (BIS does not cover this country)")
        fx = rec.get("fx")
        if fx and rec.get("currency") == "USD":
            lines.append(f"{name} | Currency: USD")
        elif fx:
            line = f"{name} | Currency: 1 USD = {fx['rate']:,.2f} {rec['currency']} (currency-api, {fx['date']})"
            if fx.get("change_12m_pct") is not None:
                line += f"; {rec['currency']} vs USD over 12 months: {fx['change_12m_pct']:+.1f}%"
            lines.append(line)
        return "\n".join(lines)

    def context_for(self, regions: List[str]) -> Tuple[str, List[Dict[str, str]]]:
        lines, sources = [], []
        for rec in self.snapshot(regions):
            line = self._line(rec)
            if not line:
                continue
            lines.append(line)
            sources.append({
                "file": f"Live open data: World Bank, BIS, currency-api ({rec.get('country', rec['region'])})",
                "region": rec["region"], "type": "Live API", "preview": " ".join(line.split())[:200],
            })
        return "\n\n".join(lines), sources


market_data = MarketData(settings.MARKET_CACHE_PATH)
