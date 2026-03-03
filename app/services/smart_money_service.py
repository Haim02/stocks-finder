"""
Smart Money / Wyckoff Accumulation Service.

Identifies stocks with quiet institutional accumulation using:
  1. OBV divergence      – OBV rising while price is flat or falling
  2. Volatility squeeze  – daily range contraction (std of % changes < 2.5%)
  3. Volume dry-up       – last 5 days volume < 85% of 30-day average
  4. Technical breakout  – fresh SMA150 crossover on above-average volume
  5. Shakeout Reversal   – V-Bottom: sharp drop ≥8% then high-volume recovery above SMA20
  6. V-Bottom Recovery   – tight 3-5 day drop (5-12%) + today's candle covers ≥50%
                           of the drop range on 1.2x volume, closing above SMA20
  7. Gorilla institutions – Vanguard, Blackrock, Fidelity, etc. in the holder list
  8. Institutional ownership concentration

Scoring:
  OBV divergence      35 pts
  Squeeze             15 pts
  Volume dry-up       10 pts
  Breakout            20 pts
  Shakeout Reversal   25 pts  (broad V-Bottom, 20-day window)
  V-Bottom Recovery   25 pts  (tight V-Bottom, 3-5 day window)
  Gorilla present     20 pts
  Inst ownership      20/10 pts

Threshold to qualify: score >= 75
"""

import logging
import time

import numpy as np
import yfinance as yf
from sklearn.linear_model import LinearRegression

from app.data.mongo_client import MongoDB
from app.services.financial_service import FinancialAnalyzer
from app.services.screener_service import ScreenerService

logger = logging.getLogger(__name__)

SMART_MONEY_URL = (
    "https://finviz.com/screener.ashx?v=211"
    "&f=cap_smallover,sh_avgvol_o500,sh_insidertrans_pos,ta_sma20_pa"
    "&ft=4"
)

GORILLAS = [
    "Vanguard", "Blackrock", "Fidelity", "State Street",
    "Berkshire", "Morgan Stanley", "Goldman Sachs",
]

QUALIFY_SCORE = 75


class SmartMoneyService:
    def __init__(self):
        self.fin_analyzer = FinancialAnalyzer()

    def run_scan(self) -> list[dict]:
        logger.info("Starting Smart Money Scan (Wyckoff Accumulation)...")

        candidates = ScreenerService.get_candidates_from_url(SMART_MONEY_URL)
        if not candidates:
            logger.warning("No candidates found from screener.")
            return []

        logger.info("Finviz returned %d candidates. Deep analyzing...", len(candidates))
        picks: list[dict] = []

        for ticker in candidates:
            try:
                result = self.analyze_stock(ticker)
                if result and result["score"] >= QUALIFY_SCORE:
                    logger.info("DETECTED: %s (Score: %d)", ticker, result["score"])
                    MongoDB.save_institutional_pick(result)
                    picks.append(result)
                else:
                    score = result["score"] if result else "N/A"
                    logger.debug("Skipping %s (Score: %s)", ticker, score)
            except Exception:
                logger.warning("Error analyzing %s", ticker, exc_info=True)

            time.sleep(0.5)

        logger.info("Scan complete. %d stocks qualified.", len(picks))
        return picks

    def analyze_stock(self, ticker: str) -> dict | None:
        stock = yf.Ticker(ticker)

        wyckoff_data = self._check_quiet_accumulation(stock)
        if not wyckoff_data:
            return None

        # Skip if neither OBV divergence nor squeeze is present
        if not (wyckoff_data["obv_divergence"] or wyckoff_data["is_squeeze"]):
            return None

        fund_basics = self._check_fundamentals(stock)
        full_financials = self.fin_analyzer.analyze(ticker) or {}

        score, reasons = self._calculate_score(wyckoff_data, fund_basics)

        return {
            "ticker": ticker,
            "score": score,
            "reasons": reasons,
            "technicals": wyckoff_data,
            "fundamentals": fund_basics,
            "full_financials": full_financials,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_quiet_accumulation(self, stock: yf.Ticker) -> dict | None:
        """
        Computes Wyckoff accumulation signals over the last 3 months.
        Returns None if there is insufficient data.
        """
        try:
            hist = stock.history(period="3mo")
            if len(hist) < 30:
                return None

            hist["OBV"] = (
                (np.sign(hist["Close"].diff()) * hist["Volume"]).fillna(0).cumsum()
            )
            recent = hist.tail(30).copy()

            # 1. Volatility squeeze
            volatility = recent["Close"].pct_change().std() * 100
            is_squeeze = bool(volatility < 2.5)

            # 2. OBV divergence (OBV rising while price is flat / declining)
            X = np.arange(len(recent)).reshape(-1, 1)
            price_slope = (
                LinearRegression().fit(X, recent["Close"].values).coef_[0]
            )
            obv_slope = (
                LinearRegression().fit(X, recent["OBV"].values).coef_[0]
            )
            norm_price_slope = price_slope / recent["Close"].mean()
            obv_divergence = bool(obv_slope > 0 and norm_price_slope < 0.0015)

            # 3. Volume dry-up (sellers exhausting)
            avg_vol_recent = recent["Volume"].tail(5).mean()
            avg_vol_month = recent["Volume"].mean()
            is_drying_up = bool(avg_vol_recent < avg_vol_month * 0.85)

            # 4. Technical breakout: fresh SMA150 crossover + above-average volume
            breakout_signal = None
            try:
                hist_1y = stock.history(period="1y")
                if len(hist_1y) > 150:
                    hist_1y["SMA150"] = hist_1y["Close"].rolling(150).mean()
                    curr_close = hist_1y["Close"].iloc[-1]
                    prev_close = hist_1y["Close"].iloc[-2]
                    curr_sma150 = hist_1y["SMA150"].iloc[-1]
                    prev_sma150 = hist_1y["SMA150"].iloc[-2]
                    avg_vol_30 = hist_1y["Volume"].tail(30).mean()
                    curr_vol = hist_1y["Volume"].iloc[-1]
                    vol_ratio = curr_vol / avg_vol_30 if avg_vol_30 > 0 else 0

                    was_below = prev_close < prev_sma150
                    is_above = curr_close > curr_sma150
                    dist_pct = (curr_close - curr_sma150) / curr_sma150

                    if was_below and is_above and dist_pct < 0.04 and vol_ratio >= 1.2:
                        breakout_signal = (
                            f"💎 חציית SMA150 עם ווליום (x{vol_ratio:.1f})"
                        )
            except Exception:
                logger.debug("Breakout check failed for stock", exc_info=True)

            # 5. Shakeout Reversal (V-Bottom): sharp drop ≥8% then high-volume
            #    bullish recovery closing above SMA20.
            shakeout_reversal = False
            shakeout_signal   = None
            try:
                hist["SMA20"] = hist["Close"].rolling(20).mean()
                w      = hist.tail(20).copy()
                closes = w["Close"].values

                # Peak must not be one of the last 3 bars so recovery is visible
                peak_pos = int(np.argmax(closes[:-3]))
                post_peak = closes[peak_pos:]
                trough_local = int(np.argmin(post_peak))
                trough_pos   = peak_pos + trough_local

                peak_price   = closes[peak_pos]
                trough_price = closes[trough_pos]
                curr_close   = closes[-1]
                curr_sma20   = w["SMA20"].values[-1]

                drop_pct     = (peak_price - trough_price) / peak_price if peak_price > 0 else 0
                recovery_pct = (curr_close - trough_price) / trough_price if trough_price > 0 else 0

                avg_vol_30d  = hist["Volume"].tail(30).mean()
                recovery_vol = w["Volume"].values[-5:].mean()
                vol_ratio    = recovery_vol / avg_vol_30d if avg_vol_30d > 0 else 0

                if (
                    drop_pct     >= 0.08
                    and recovery_pct >= 0.05
                    and trough_pos   <  len(closes) - 2
                    and not np.isnan(curr_sma20)
                    and curr_close   >  curr_sma20
                    and vol_ratio    >= 1.3
                ):
                    shakeout_reversal = True
                    shakeout_signal   = (
                        f"🔄 Shakeout Reversal: ירידה {drop_pct:.0%}, "
                        f"התאוששות {recovery_pct:.0%} מעל SMA20 "
                        f"(ווליום x{vol_ratio:.1f})"
                    )
            except Exception:
                logger.debug("Shakeout reversal check failed", exc_info=True)

            # 6. V-Bottom Recovery: tight 3-5 day drop (5-12%) followed by today's
            #    bullish candle that covers ≥50% of that drop range on 1.2x volume,
            #    closing above SMA20.
            vbottom_recovery = False
            vbottom_signal   = None
            try:
                hist["SMA20"] = hist["Close"].rolling(20).mean()
                if len(hist) >= 25:
                    # 6 rows: 5 pre-today bars + today
                    w6 = hist.tail(6).copy()
                    arr = w6["Close"].values
                    today_close = float(arr[-1])
                    today_vol   = float(w6["Volume"].values[-1])
                    today_sma20 = float(w6["SMA20"].values[-1])

                    pre = arr[:-1]                     # 5 bars before today
                    peak_idx    = int(np.argmax(pre))
                    peak_price  = float(pre[peak_idx])

                    # Trough is the minimum in the bars from peak up to (not incl.) today
                    trough_price = float(np.min(pre[peak_idx:]))

                    drop_range  = peak_price - trough_price
                    drop_pct    = drop_range / peak_price if peak_price > 0 else 0

                    # How much of the drop range did today's close recover?
                    recovery_from_trough = today_close - trough_price
                    recovery_ratio = (
                        recovery_from_trough / drop_range if drop_range > 0 else 0
                    )

                    avg_vol_30d = hist["Volume"].tail(30).mean()
                    vol_ratio   = today_vol / avg_vol_30d if avg_vol_30d > 0 else 0

                    if (
                        0.05 <= drop_pct <= 0.12
                        and recovery_ratio >= 0.50
                        and not np.isnan(today_sma20)
                        and today_close > today_sma20
                        and vol_ratio   >= 1.2
                    ):
                        vbottom_recovery = True
                        vbottom_signal   = (
                            f"📈 V-Bottom Recovery: ירידה {drop_pct:.0%} ב-3-5 ימים, "
                            f"שיחזור {recovery_ratio:.0%} מהטווח מעל SMA20 "
                            f"(ווליום x{vol_ratio:.1f})"
                        )
            except Exception:
                logger.debug("V-Bottom recovery check failed", exc_info=True)

            return {
                "is_squeeze": is_squeeze,
                "volatility": round(volatility, 2),
                "obv_divergence": obv_divergence,
                "is_drying_up": is_drying_up,
                "breakout_signal": breakout_signal,
                "shakeout_reversal": shakeout_reversal,
                "shakeout_signal": shakeout_signal,
                "vbottom_recovery": vbottom_recovery,
                "vbottom_signal": vbottom_signal,
            }

        except Exception:
            logger.warning("_check_quiet_accumulation failed", exc_info=True)
            return None

    def _check_fundamentals(self, stock: yf.Ticker) -> dict:
        info = {}
        try:
            info = stock.info
        except Exception:
            logger.debug("yfinance .info failed", exc_info=True)

        rev_growth = info.get("revenueGrowth", 0) or 0
        inst_own = info.get("heldPercentInstitutions", 0) or 0

        found_gorillas: list[str] = []
        try:
            holders = stock.institutional_holders
            if holders is not None and not holders.empty:
                names = holders["Holder"].astype(str).tolist()
                for h in names:
                    for g in GORILLAS:
                        if g.lower() in h.lower():
                            found_gorillas.append(g)
        except Exception:
            logger.debug("Institutional holders fetch failed", exc_info=True)

        return {
            "revenue_growth": round(rev_growth * 100, 1),
            "institutional_ownership": round(inst_own * 100, 1),
            "gorillas": list(set(found_gorillas)),
            "has_gorillas": len(found_gorillas) > 0,
        }

    def _calculate_score(self, tech: dict, fund: dict) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        if tech["obv_divergence"]:
            score += 35
            reasons.append("סטיית OBV (איסוף שקט)")

        if tech["is_squeeze"]:
            score += 15
            reasons.append(f"כיווץ תנודתיות ({tech['volatility']}%)")

        if tech["is_drying_up"]:
            score += 10
            reasons.append("התייבשות מוכרים (ווליום נמוך)")

        if tech.get("breakout_signal"):
            score += 20
            reasons.append(tech["breakout_signal"])

        if tech.get("shakeout_reversal"):
            score += 25
            reasons.append(tech["shakeout_signal"])

        if tech.get("vbottom_recovery"):
            score += 25
            reasons.append(tech["vbottom_signal"])

        if fund["has_gorillas"]:
            score += 20
            gorilla_names = ", ".join(fund["gorillas"][:2])
            reasons.append(f"גורילות: {gorilla_names}")

        if fund["institutional_ownership"] > 80:
            score += 20
            reasons.append("אחזקה מוסדית כבדה (>80%)")
        elif fund["institutional_ownership"] > 50:
            score += 10
            reasons.append("אחזקה מוסדית בינונית (>50%)")

        return score, reasons
