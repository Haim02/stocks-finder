"""
API Hub — Centralized premium data fetcher.

Sources (all keys from os.getenv — never hardcoded):
  FRED API        — US macro: Fed Rate, CPI year-over-year
  SEC EDGAR       — Recent 10-K/10-Q filing dates, CIK lookup (free, no key)
  yfinance        — Short ratio, institutional %, always-available fallback
  Aletheia        — Optional override for short ratio / institutional data
  Marketstack     — Corporate actions: splits + dividends
  Alpha Vantage   — Crypto daily prices (BTC, ETH, etc.)
  Finage          — Crypto prices fallback

Design principles:
  - Every method returns {} / None on failure — never raises to callers
  - Results cached in _CACHE dict for the process lifetime (one scan run)
  - All network calls use a shared requests.Session with a UA header
"""

import logging
import os
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)

# ── Shared HTTP session ────────────────────────────────────────────────────
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "stocks-finder-bot/1.0 (research project)",
    "Accept":     "application/json",
})

# ── In-process result cache ────────────────────────────────────────────────
_CACHE: dict = {}


def _get(url: str, params: dict | None = None, timeout: int = 10) -> dict:
    """Generic JSON GET that swallows all errors and returns {}."""
    try:
        r = _SESSION.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.debug("API GET failed: %s — %s", url, exc)
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# FRED — US Macroeconomics
# ══════════════════════════════════════════════════════════════════════════════

def _fred_obs(series_id: str, limit: int = 50,
              start: str | None = None, end: str | None = None) -> list[dict]:
    """Fetch raw FRED observations. Returns [] if FRED_API_KEY is absent."""
    key = os.getenv("FRED_API_KEY")
    if not key:
        return []
    params: dict = {
        "series_id":  series_id,
        "api_key":    key,
        "file_type":  "json",
        "sort_order": "desc",
        "limit":      limit,
    }
    if start:
        params["observation_start"] = start
    if end:
        params["observation_end"] = end
    return _get(
        "https://api.stlouisfed.org/fred/series/observations", params=params
    ).get("observations", [])


def get_macro_context() -> dict:
    """
    Returns current US macro indicators from FRED.

    Keys:
      fed_rate : float | "N/A"  — effective federal funds rate (%)
      cpi_yoy  : float | "N/A"  — CPI year-over-year inflation (%)
      regime   : str             — HIGH_RATE / ELEVATED / NORMAL / LOW_RATE
      notes    : str             — Hebrew summary for the AI options prompt
    """
    if "macro_context" in _CACHE:
        return _CACHE["macro_context"]

    result: dict = {
        "fed_rate": "N/A",
        "cpi_yoy":  "N/A",
        "regime":   "UNKNOWN",
        "notes":    "נתוני מאקרו לא זמינים — FRED_API_KEY חסר או שגיאת רשת.",
    }

    # Fed Funds Rate (latest)
    fed_rate: float | None = None
    obs = _fred_obs("FEDFUNDS", limit=1)
    if obs:
        try:
            fed_rate = float(obs[0]["value"])
            result["fed_rate"] = round(fed_rate, 2)
        except (ValueError, KeyError):
            pass

    # CPI YoY — fetch ~14 months to compute % change
    end_str   = date.today().strftime("%Y-%m-%d")
    start_str = (date.today() - timedelta(days=420)).strftime("%Y-%m-%d")
    cpi_obs   = _fred_obs("CPIAUCSL", limit=50, start=start_str, end=end_str)
    if len(cpi_obs) >= 13:
        try:
            chron = list(reversed(cpi_obs))       # oldest → newest
            latest = float(chron[-1]["value"])
            yr_ago = float(chron[-13]["value"])
            result["cpi_yoy"] = round((latest - yr_ago) / yr_ago * 100, 2)
        except (ValueError, KeyError, ZeroDivisionError):
            pass

    # Regime label
    if fed_rate is not None:
        result["regime"] = (
            "HIGH_RATE"  if fed_rate > 5.0 else
            "ELEVATED"   if fed_rate > 3.5 else
            "NORMAL"     if fed_rate > 1.5 else
            "LOW_RATE"
        )

    # Hebrew summary for options AI
    rate_str = f"{result['fed_rate']}%" if result["fed_rate"] != "N/A" else "לא ידוע"
    cpi_str  = f"{result['cpi_yoy']}%" if result["cpi_yoy"]  != "N/A" else "לא ידוע"
    high_rate = result["regime"] in ("HIGH_RATE", "ELEVATED")
    result["notes"] = (
        f"ריבית פד: {rate_str}  |  אינפלציה (YoY): {cpi_str}  |  משטר: {result['regime']}. "
        + (
            "סביבת ריבית גבוהה — פרמיית אופציות גבוהה יותר, עדיפות למכירת פרמיה עם מרווחים רחבים."
            if high_rate else
            "סביבת ריבית נמוכה — מרווחים צרים, בכורה לגאמה-הדוקה וניהול סיכון קפדני."
        )
    )

    _CACHE["macro_context"] = result
    return result


def get_fred_series(series_id: str, start: str, end: str) -> dict[str, float]:
    """
    Returns {date_str: value} for a FRED series between start and end dates.
    Used in train_model.py to join macro features to historical OHLCV data.
    Cached per (series_id, start, end).
    """
    ck = f"fred_{series_id}_{start}_{end}"
    if ck in _CACHE:
        return _CACHE[ck]
    obs    = _fred_obs(series_id, limit=500, start=start, end=end)
    result = {}
    for o in obs:
        try:
            result[o["date"]] = float(o["value"])
        except (ValueError, KeyError):
            continue
    _CACHE[ck] = result
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SEC EDGAR — Institutional data + recent filings
# ══════════════════════════════════════════════════════════════════════════════

_EDGAR_MAP: dict | None = None     # loaded once: company_tickers.json


def _edgar_map() -> dict:
    global _EDGAR_MAP
    if _EDGAR_MAP is None:
        _EDGAR_MAP = _get(
            "https://www.sec.gov/files/company_tickers.json", timeout=15
        )
    return _EDGAR_MAP or {}


def get_edgar_cik(ticker: str) -> str | None:
    """Returns zero-padded 10-digit CIK, or None if the ticker is not found."""
    t  = ticker.upper()
    ck = f"cik_{t}"
    if ck in _CACHE:
        return _CACHE[ck]
    for v in _edgar_map().values():
        if v.get("ticker", "").upper() == t:
            cik = str(v["cik_str"]).zfill(10)
            _CACHE[ck] = cik
            return cik
    _CACHE[ck] = None
    return None


def get_institutional_data(ticker: str) -> dict:
    """
    Enriches a ticker with institutional + short-interest data.

    Returns:
      last_filing        : str   — date of most recent 10-K/10-Q (SEC EDGAR)
      last_filing_form   : str   — "10-K" or "10-Q"
      short_ratio        : float — days-to-cover
      short_pct_float    : float — short interest as % of float
      inst_pct_held      : float — % shares held by institutions
      short_squeeze_risk : str   — HIGH / MEDIUM / LOW

    Data chain:
      1. SEC EDGAR (free) for filing date
      2. yfinance   for short/institutional metrics
      3. Aletheia   if ALETHEIA_API_KEY is set (overrides yfinance where present)
    """
    ck = f"inst_{ticker.upper()}"
    if ck in _CACHE:
        return _CACHE[ck]

    result: dict = {
        "last_filing":        "N/A",
        "last_filing_form":   "N/A",
        "short_ratio":        "N/A",
        "short_pct_float":    "N/A",
        "inst_pct_held":      "N/A",
        "short_squeeze_risk": "LOW",
    }

    # 1. SEC EDGAR — recent 10-K/10-Q date
    try:
        cik = get_edgar_cik(ticker)
        if cik:
            sub      = _get(f"https://data.sec.gov/submissions/CIK{cik}.json", timeout=12)
            filings  = sub.get("filings", {}).get("recent", {})
            forms    = filings.get("form", [])
            dates    = filings.get("filingDate", [])
            for form, dt in zip(forms, dates):
                if form in ("10-K", "10-Q"):
                    result["last_filing"]      = dt
                    result["last_filing_form"] = form
                    break
    except Exception:
        logger.debug("SEC EDGAR failed for %s", ticker)

    # 2. yfinance — always-available short/institutional metrics
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        sr   = info.get("shortRatio")
        spf  = info.get("shortPercentOfFloat")
        inst = info.get("institutionsPercentHeld") or info.get("heldPercentInstitutions")

        if sr   is not None: result["short_ratio"]     = round(float(sr),   2)
        if spf  is not None: result["short_pct_float"] = round(float(spf) * 100, 1)
        if inst is not None: result["inst_pct_held"]   = round(float(inst) * 100, 1)

        # Short squeeze risk classification
        pct  = float(spf or 0) * 100
        days = float(sr or 0)
        result["short_squeeze_risk"] = (
            "HIGH"   if pct > 20 and days > 7  else
            "MEDIUM" if pct > 10 or  days > 4  else
            "LOW"
        )
    except Exception:
        logger.debug("yfinance institutional data failed for %s", ticker)

    # 3. Aletheia (optional — overrides above if key present)
    aletheia_key = os.getenv("ALETHEIA_API_KEY")
    if aletheia_key:
        try:
            data = _get(
                f"https://aletheia-ams.com/api/stock/{ticker}/statistics",
                params={"token": aletheia_key},
            )
            if data:
                if v := data.get("ShortRatio"):
                    result["short_ratio"] = round(float(v), 2)
                if v := data.get("PercentHeldByInstitutions"):
                    result["inst_pct_held"] = round(float(v) * 100, 1)
                if v := data.get("DebtToEquityRatio"):
                    result["dte_aletheia"] = round(float(v), 2)
        except Exception:
            logger.debug("Aletheia API failed for %s", ticker)

    _CACHE[ck] = result
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Marketstack — Corporate Actions (splits + dividends)
# ══════════════════════════════════════════════════════════════════════════════

def get_corporate_actions(ticker: str, start_date: str, end_date: str) -> dict:
    """
    Returns splits and dividends for `ticker` between start_date and end_date.

    Used in train_model.py to remove rows distorted by corporate events.
    Falls back to yfinance .actions when MARKETSTACK_API_KEY is absent.

    Returns:
      {"splits": [{date, split_factor}, ...], "dividends": [{date, amount}, ...]}
    """
    ck = f"ca_{ticker.upper()}_{start_date}_{end_date}"
    if ck in _CACHE:
        return _CACHE[ck]

    result: dict = {"splits": [], "dividends": []}
    ms_key = os.getenv("MARKETSTACK_API_KEY")

    if ms_key:
        _base = "https://api.marketstack.com/v1"
        common = {"access_key": ms_key, "symbols": ticker,
                  "date_from": start_date, "date_to": end_date, "limit": 100}
        try:
            for item in _get(f"{_base}/splits", params=common).get("data", []):
                result["splits"].append({
                    "date":         (item.get("date") or "")[:10],
                    "split_factor": float(item.get("split_factor", 1.0)),
                })
        except Exception:
            logger.debug("Marketstack splits failed for %s", ticker)
        try:
            for item in _get(f"{_base}/dividends", params=common).get("data", []):
                result["dividends"].append({
                    "date":   (item.get("date") or "")[:10],
                    "amount": float(item.get("dividend", 0.0)),
                })
        except Exception:
            logger.debug("Marketstack dividends failed for %s", ticker)
    else:
        # yfinance fallback — no API key needed
        try:
            import yfinance as yf
            import pandas as pd
            actions = yf.Ticker(ticker).actions
            if actions is not None and not actions.empty:
                mask = (
                    (actions.index >= pd.Timestamp(start_date)) &
                    (actions.index <= pd.Timestamp(end_date))
                )
                for idx, row in actions[mask].iterrows():
                    d = idx.strftime("%Y-%m-%d")
                    if row.get("Stock Splits", 0) > 0:
                        result["splits"].append(
                            {"date": d, "split_factor": float(row["Stock Splits"])}
                        )
                    if row.get("Dividends", 0) > 0:
                        result["dividends"].append(
                            {"date": d, "amount": float(row["Dividends"])}
                        )
        except Exception:
            logger.debug("yfinance corporate actions fallback failed for %s", ticker)

    _CACHE[ck] = result
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Alpha Vantage / Finage — Crypto Momentum
# ══════════════════════════════════════════════════════════════════════════════

def get_crypto_momentum(symbol: str) -> dict | None:
    """
    Returns price data for a crypto asset (e.g. "BTC", "ETH").

    Keys: symbol, price, change_pct_24h, volume, source.
    Tries Alpha Vantage first, then Finage.  Returns None when both fail.
    """
    ck = f"crypto_{symbol.upper()}"
    if ck in _CACHE:
        return _CACHE[ck]

    result: dict | None = None

    # ── Alpha Vantage ──────────────────────────────────────────────────────
    av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if av_key:
        try:
            data = _get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "DIGITAL_CURRENCY_DAILY",
                    "symbol":   symbol,
                    "market":   "USD",
                    "apikey":   av_key,
                },
                timeout=15,
            )
            ts = data.get("Time Series (Digital Currency Daily)", {})
            if ts:
                dates  = sorted(ts.keys(), reverse=True)
                latest = ts[dates[0]]
                prev   = ts[dates[1]] if len(dates) > 1 else latest
                # field names differ between AV versions
                close_k = "4a. close (USD)" if "4a. close (USD)" in latest else "4. close"
                price   = float(latest.get(close_k, 0))
                prev_p  = float(prev.get(close_k, price))
                result  = {
                    "symbol":         symbol.upper(),
                    "price":          round(price, 2),
                    "change_pct_24h": round((price - prev_p) / prev_p * 100, 2) if prev_p else 0,
                    "volume":         float(latest.get("5. volume", 0)),
                    "source":         "AlphaVantage",
                }
        except Exception:
            logger.debug("Alpha Vantage crypto failed for %s", symbol)

    # ── Finage fallback ───────────────────────────────────────────────────
    fg_key = os.getenv("FINAGE_API_KEY")
    if fg_key and not result:
        try:
            data = _get(
                f"https://api.finage.co.uk/agg/crypto/prev-close/{symbol.upper()}USD",
                params={"apikey": fg_key},
            )
            for r in data.get("results", []):
                price  = float(r.get("c", 0))
                open_p = float(r.get("o", price))
                result = {
                    "symbol":         symbol.upper(),
                    "price":          round(price, 2),
                    "change_pct_24h": round((price - open_p) / open_p * 100, 2) if open_p else 0,
                    "volume":         r.get("v", 0),
                    "source":         "Finage",
                }
                break
        except Exception:
            logger.debug("Finage crypto failed for %s", symbol)

    if result:
        _CACHE[ck] = result
    return result
