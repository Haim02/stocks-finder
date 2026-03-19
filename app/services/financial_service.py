import logging

import finnhub
import numpy as np
import yfinance as yf

from app.core.config import settings

logger = logging.getLogger(__name__)


def _fmt_num(v: float | None) -> str:
    """Format a raw dollar value to a readable string (B/M)."""
    if v is None or v == 0:
        return "N/A"
    if abs(v) >= 1e9:
        return f"${v / 1e9:.1f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:.0f}M"
    return f"${v:,.0f}"


class FinancialAnalyzer:
    def __init__(self):
        self.client = (
            finnhub.Client(api_key=settings.FINNHUB_API_KEY)
            if settings.FINNHUB_API_KEY
            else None
        )

    def analyze(self, ticker: str) -> dict | None:
        """
        Returns a dict with price, technicals (SMA150 crossover, SMA50 breakout,
        bullish engulfing), quarterly financials (revenue, net income, efficiency),
        5-year margin trends, balance sheet health, FCF analysis, and valuation
        ratios.  Returns None if data is unavailable.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            if not current_price:
                return None

            description = (
                info.get("longBusinessSummary") or info.get("description", "")
            )[:800]

            technical_signal = None
            trend_status = "מגמה לא ברורה"
            vol_ratio = 1.0

            # --- Technical analysis ---
            try:
                hist = stock.history(period="1y")
                if len(hist) > 150:
                    hist["SMA50"]  = hist["Close"].rolling(50).mean()
                    hist["SMA150"] = hist["Close"].rolling(150).mean()

                    curr_close  = hist["Close"].iloc[-1]
                    prev_close  = hist["Close"].iloc[-2]
                    curr_open   = hist["Open"].iloc[-1]
                    curr_sma150 = hist["SMA150"].iloc[-1]
                    prev_sma150 = hist["SMA150"].iloc[-2]
                    curr_sma50  = hist["SMA50"].iloc[-1]
                    prev_sma50  = hist["SMA50"].iloc[-2]

                    avg_vol_30 = hist["Volume"].tail(30).mean()
                    curr_vol   = hist["Volume"].iloc[-1]
                    vol_ratio  = round(curr_vol / avg_vol_30, 1) if avg_vol_30 > 0 else 0

                    was_below = prev_close < prev_sma150
                    is_above  = curr_close > curr_sma150
                    dist_pct  = (curr_close - curr_sma150) / curr_sma150

                    if was_below and is_above and dist_pct < 0.04:
                        technical_signal = f"💎 חציית SMA150 טרייה! (+{dist_pct * 100:.1f}%)"
                        trend_status = "✅ התחלת מגמה (מעל SMA150)"
                    elif curr_close > curr_sma150:
                        trend_status = "✅ במגמה עולה (מעל SMA150)"
                        if prev_close < prev_sma50 and curr_close > curr_sma50:
                            technical_signal = f"🔥 פריצת SMA50 (בתוך מגמה עולה, Vol x{vol_ratio})"
                    else:
                        trend_status = "⛔ מתחת ל-SMA150 (מגמת ירידה)"

                    if not technical_signal:
                        prev_open = hist["Open"].iloc[-2]
                        if (
                            prev_close < prev_open
                            and curr_close > curr_open
                            and curr_close > prev_open
                            and curr_open < prev_close
                        ):
                            technical_signal = "🕯️ נר עוטף שורי (Bullish Engulfing)"

            except Exception:
                logger.warning("Technical analysis failed for %s", ticker, exc_info=True)

            financial_data: dict = {
                "current_price":  round(current_price, 2),
                "market_cap":     info.get("marketCap", 0),
                "description":    description,
                "technical_signal": technical_signal,
                "trend_status":   trend_status,
                "volume_ratio":   vol_ratio,
                "revenue":        {"curr": 0, "prev": 0, "change": 0},
                "net_income":     {"curr": 0, "prev": 0, "change": 0},
                "efficiency":     {"curr": None, "prev": None},
                "target_price":   round(current_price * 1.25, 2),
                "stop_loss":      round(current_price * 0.93, 2),
                # enriched defaults (filled below)
                "gross_margin_5y":    [],
                "operating_margin_5y": [],
                "net_margin_5y":      [],
                "debt_to_equity":     "N/A",
                "current_ratio":      "N/A",
                "total_cash":         0,
                "total_debt":         0,
                "fcf_history":        [],
                "fcf_growth":         "N/A",
                "pe_ratio":           "N/A",
                "peg_ratio":          "N/A",
            }

            # --- Quarterly financials ---
            try:
                q_fin = stock.quarterly_financials
                if not q_fin.empty and q_fin.shape[1] >= 2:
                    def get_val(key, idx):
                        if key in q_fin.index and len(q_fin.columns) > idx:
                            val = q_fin.loc[key].iloc[idx]
                            return val if val == val else 0
                        return 0

                    r_curr = get_val("Total Revenue", 0) or get_val("Operating Revenue", 0)
                    r_prev = get_val("Total Revenue", 1) or get_val("Operating Revenue", 1)
                    if r_prev:
                        financial_data["revenue"] = {
                            "curr":   r_curr,
                            "prev":   r_prev,
                            "change": round((r_curr - r_prev) / r_prev * 100, 2),
                        }

                    n_curr = get_val("Net Income", 0)
                    n_prev = get_val("Net Income", 1)
                    if n_prev:
                        financial_data["net_income"] = {
                            "curr":   n_curr,
                            "prev":   n_prev,
                            "change": round((n_curr - n_prev) / abs(n_prev) * 100, 2),
                        }

                    op_exp_curr = get_val("Total Operating Expenses", 0)
                    op_exp_prev = get_val("Total Operating Expenses", 1)
                    if op_exp_curr == 0:
                        op_exp_curr = r_curr - get_val("Operating Income", 0)
                    if op_exp_prev == 0:
                        op_exp_prev = r_prev - get_val("Operating Income", 1)

                    def calc_eff(exp, rev):
                        return round(exp / rev * 100, 2) if rev else None

                    financial_data["efficiency"]["curr"] = calc_eff(op_exp_curr, r_curr)
                    financial_data["efficiency"]["prev"] = calc_eff(op_exp_prev, r_prev)

            except Exception:
                logger.warning("Quarterly financials failed for %s", ticker, exc_info=True)

            # --- Enriched institutional data (5-yr margins, FCF, valuation) ---
            try:
                enriched = self._fetch_enriched(stock, info)
                financial_data.update(enriched)
            except Exception:
                logger.debug("Enriched data fetch failed for %s", ticker, exc_info=True)

            # --- Institutional ownership + SEC EDGAR (api_hub) ---
            try:
                from app.services.api_hub import get_institutional_data
                inst = get_institutional_data(ticker)
                if inst:
                    financial_data.update(inst)
            except Exception:
                logger.debug("Institutional data fetch skipped for %s", ticker)

            return financial_data

        except Exception:
            logger.error("Data error for %s", ticker, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Institutional enrichment: 5-year margins, balance sheet, FCF
    # ------------------------------------------------------------------

    def _fetch_enriched(self, stock: yf.Ticker, info: dict) -> dict:
        """
        Fetches institutional-grade data from yfinance annual statements:
          - 5-year gross / operating / net margin trends
          - Balance sheet: D/E ratio, current ratio, cash, debt
          - Free cash flow history and 3-year CAGR
          - Valuation: P/E and PEG from yfinance info
        All failures are silenced so they don't break the main analyze() call.
        """
        result: dict = {
            "gross_margin_5y":    [],
            "operating_margin_5y": [],
            "net_margin_5y":      [],
            "debt_to_equity":     "N/A",
            "current_ratio":      "N/A",
            "total_cash":         0,
            "total_debt":         0,
            "fcf_history":        [],
            "fcf_growth":         "N/A",
            "pe_ratio":           "N/A",
            "peg_ratio":          "N/A",
        }

        # Valuation ratios (already in info — no extra API call)
        pe = info.get("trailingPE") or info.get("forwardPE")
        if pe:
            result["pe_ratio"] = round(float(pe), 1)
        peg = info.get("pegRatio")
        if peg:
            result["peg_ratio"] = round(float(peg), 2)

        # ── Annual income statement → 5-year margin trends ───────────
        try:
            inc = stock.income_stmt
            if inc is not None and not inc.empty:
                # Sort newest → oldest
                inc = inc[sorted(inc.columns, reverse=True)]

                def _row(df, *keys):
                    for k in keys:
                        if k in df.index:
                            return df.loc[k].values
                    return None

                rev = _row(inc, "Total Revenue", "Operating Revenue")
                gp  = _row(inc, "Gross Profit")
                op  = _row(inc, "Operating Income", "EBIT")
                ni  = _row(inc, "Net Income")

                if rev is not None:
                    n = min(5, len(rev))

                    def _margins(numer):
                        if numer is None:
                            return []
                        out = []
                        for i in range(n):
                            try:
                                r, x = float(rev[i]), float(numer[i])
                                if r and r == r and x == x:
                                    out.append(round(x / r * 100, 1))
                            except (TypeError, ValueError, ZeroDivisionError):
                                pass
                        return out

                    result["gross_margin_5y"]    = _margins(gp)
                    result["operating_margin_5y"] = _margins(op)
                    result["net_margin_5y"]       = _margins(ni)
        except Exception:
            logger.debug("Annual income stmt fetch failed", exc_info=True)

        # ── Annual balance sheet → D/E, current ratio, cash, debt ────
        try:
            bs = stock.balance_sheet
            if bs is not None and not bs.empty:
                bs = bs[sorted(bs.columns, reverse=True)]

                def _bval(*keys):
                    for k in keys:
                        if k in bs.index:
                            v = bs.loc[k].iloc[0]
                            if v == v:   # NaN guard
                                return float(v)
                    return None

                cash = _bval(
                    "Cash And Cash Equivalents",
                    "Cash Cash Equivalents And Short Term Investments",
                    "Cash And Short Term Investments",
                )
                if cash:
                    result["total_cash"] = cash

                debt = _bval("Total Debt", "Long Term Debt And Capital Lease Obligation")
                if debt is None:
                    ld = _bval("Long Term Debt") or 0
                    sd = _bval("Current Debt", "Short Long Term Debt") or 0
                    debt = ld + sd if (ld or sd) else None
                if debt:
                    result["total_debt"] = debt

                equity = _bval(
                    "Stockholders Equity",
                    "Common Stock Equity",
                    "Total Equity Gross Minority Interest",
                )
                if equity and debt and equity != 0:
                    result["debt_to_equity"] = round(debt / equity, 2)

                ca = _bval("Current Assets", "Total Current Assets")
                cl = _bval(
                    "Current Liabilities",
                    "Total Current Liabilities Net Minority Interest",
                )
                if ca and cl and cl != 0:
                    result["current_ratio"] = round(ca / cl, 2)
        except Exception:
            logger.debug("Balance sheet fetch failed", exc_info=True)

        # ── Annual cash flow → FCF history + 3-year CAGR ─────────────
        try:
            cf = stock.cashflow
            if cf is not None and not cf.empty:
                cf = cf[sorted(cf.columns, reverse=True)]

                def _cfrow(*keys):
                    for k in keys:
                        if k in cf.index:
                            return cf.loc[k].values
                    return None

                raw = _cfrow("Free Cash Flow")
                if raw is None:
                    ocf   = _cfrow("Operating Cash Flow", "Cash Flow From Continuing Operations")
                    capex = _cfrow("Capital Expenditure")
                    if ocf is not None and capex is not None:
                        n = min(5, len(ocf), len(capex))
                        raw = [
                            float(ocf[i]) + float(capex[i])   # capex is negative in yf
                            for i in range(n)
                            if ocf[i] == ocf[i] and capex[i] == capex[i]
                        ]

                if raw is not None:
                    fcf_clean = [float(v) for v in raw[:5] if v == v]
                    result["fcf_history"] = fcf_clean
                    # 3-year CAGR: compare year 0 vs year 2 (2-period)
                    if len(fcf_clean) >= 3 and fcf_clean[2] > 0 and fcf_clean[0] > 0:
                        cagr = (fcf_clean[0] / fcf_clean[2]) ** 0.5 - 1
                        result["fcf_growth"] = round(cagr * 100, 1)
        except Exception:
            logger.debug("FCF fetch failed", exc_info=True)

        return result
