"""
Options Service — Daily Options Brief pipeline.

Responsibilities:
  1. Fetch current SPX price (^GSPC) and VIX (^VIX).
  2. Build a Tastytrade-style 0DTE SPY iron condor (SPY is used as the SPX
     proxy because SPX index options are not reliably available via yfinance).
  3. Build credit-spread setups for individual stock candidates.

Greeks (delta, theta) are computed in-house via Black-Scholes using only
the Python standard library — no scipy dependency needed.

0DTE logic follows Tastytrade methodology:
  - Short strikes targeted at 0.10–0.15 delta
  - Spread width: $3 (low VIX) or $5 (VIX > 20)
  - Stop-loss : 2× credit collected
  - Profit target: 50% of credit collected
  - Minimum risk/reward enforced: credit ≥ width / 4  (1:3 RR)
"""

import logging
import math
from datetime import date, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
RISK_FREE_RATE = 0.05          # approximate annual risk-free rate

SPY_TICKER = "SPY"             # proxy for SPX options (widely available via yfinance)

TARGET_DELTA_0DTE    = (0.10, 0.15)   # delta range for 0DTE short strikes
TARGET_DELTA_STOCK   = (0.25, 0.35)   # delta range for stock credit spreads

MIN_RR_DENOMINATOR  = 4.0     # credit must be ≥ width/4  →  1:3 risk/reward
PROFIT_TARGET_PCT   = 0.50    # close at 50% of credit
STOP_LOSS_MULT      = 2.0     # close at 2× credit (debit)


# ── Black-Scholes helpers ──────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
               opt_type: str) -> tuple[float, float]:
    """
    Returns (delta, theta_per_day) for a European option.
    Put delta is negative.  Theta is in dollar-per-day units
    relative to the option price (not per contract).
    """
    if T <= 1e-8 or sigma <= 1e-8 or S <= 0 or K <= 0:
        if opt_type == "call":
            return (1.0 if S > K else 0.0), 0.0
        return (-1.0 if S < K else 0.0), 0.0

    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT

    common_theta = -(S * _norm_pdf(d1) * sigma) / (2.0 * sqrtT) / 365.0

    if opt_type == "call":
        delta = _norm_cdf(d1)
        theta = common_theta - r * K * math.exp(-r * T) * _norm_cdf(d2) / 365.0
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = common_theta + r * K * math.exp(-r * T) * _norm_cdf(-d2) / 365.0

    return delta, theta


def _mid(row) -> float:
    """Bid/ask midpoint; falls back to lastPrice."""
    bid = float(row.get("bid") or 0)
    ask = float(row.get("ask") or 0)
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return float(row.get("lastPrice") or 0)


# ── Main service ───────────────────────────────────────────────────────────

class OptionsService:
    """Fetches and structures options data for the Daily Options Brief."""

    # ------------------------------------------------------------------
    # Market context
    # ------------------------------------------------------------------

    def get_market_context(self) -> dict:
        """Returns current SPX price and VIX."""
        try:
            spx = float(yf.Ticker("^GSPC").fast_info["lastPrice"])
        except Exception:
            spx = 0.0
            logger.warning("Could not fetch ^GSPC price")

        try:
            vix = float(yf.Ticker("^VIX").fast_info["lastPrice"])
        except Exception:
            vix = 0.0
            logger.warning("Could not fetch ^VIX")

        return {"spx_price": round(spx, 2), "vix": round(vix, 2)}

    # ------------------------------------------------------------------
    # 0DTE SPY iron condor  (SPX proxy)
    # ------------------------------------------------------------------

    def build_0dte_spx_setup(self, vix: float) -> dict | None:
        """
        Constructs an iron condor on SPY targeting the nearest 0DTE expiration.
        Spread width is widened when VIX > 20 to collect more premium.
        Returns None when options data is unavailable.
        """
        try:
            spy   = yf.Ticker(SPY_TICKER)
            S     = float(spy.fast_info["lastPrice"])
            exps  = spy.options
            if not exps:
                return None

            today      = date.today().strftime("%Y-%m-%d")
            expiry_str = next((e for e in sorted(exps) if e >= today), None)
            if not expiry_str:
                return None

            days_out = max((date.fromisoformat(expiry_str) - date.today()).days, 0)
            T        = max(days_out / 365.0, 0.5 / 365.0)  # at least half a day

            chain      = spy.option_chain(expiry_str)
            spread_w   = 5 if vix > 20 else 3

            put_spread  = self._find_credit_spread(chain.puts,  S, T, "put",  spread_w)
            call_spread = self._find_credit_spread(chain.calls, S, T, "call", spread_w)

            if not put_spread and not call_spread:
                logger.warning("0DTE: could not construct any spread (no strikes in delta range?)")
                return None

            total_credit = (put_spread["credit"] if put_spread else 0.0) + \
                           (call_spread["credit"] if call_spread else 0.0)

            return {
                "expiry":        expiry_str,
                "spy_price":     round(S, 2),
                "spread_width":  spread_w,
                "put_spread":    put_spread,
                "call_spread":   call_spread,
                "total_credit":  round(total_credit, 2),
                "stop_loss":     round(total_credit * STOP_LOSS_MULT, 2),
                "profit_target": round(total_credit * PROFIT_TARGET_PCT, 2),
            }

        except Exception:
            logger.warning("build_0dte_spx_setup failed", exc_info=True)
            return None

    def _find_credit_spread(self, df, S: float, T: float,
                             opt_type: str, width: float) -> dict | None:
        """
        Scans the chain for the short strike closest to the delta target range,
        then pairs it with a long strike `width` points further OTM.
        Returns None when no qualifying strike exists or RR is too poor.
        """
        lo_d, hi_d = TARGET_DELTA_0DTE
        r = RISK_FREE_RATE
        candidates: list[dict] = []

        for _, row in df.iterrows():
            K  = float(row["strike"])
            iv = float(row.get("impliedVolatility") or 0)
            if iv <= 0:
                continue
            delta, theta = _bs_greeks(S, K, T, r, iv, opt_type)
            if lo_d <= abs(delta) <= hi_d:
                candidates.append({
                    "strike": K, "delta": round(delta, 3),
                    "theta": round(theta, 5), "iv": round(iv, 3),
                    "mid": _mid(row),
                })

        if not candidates:
            return None

        mid_target = (lo_d + hi_d) / 2
        short = min(candidates, key=lambda c: abs(abs(c["delta"]) - mid_target))

        # Long leg
        long_target_K = short["strike"] - width if opt_type == "put" \
                        else short["strike"] + width
        df2 = df.copy()
        df2["_dist"] = abs(df2["strike"] - long_target_K)
        long_row     = df2.nsmallest(1, "_dist").iloc[0]
        long_K       = float(long_row["strike"])
        long_iv      = float(long_row.get("impliedVolatility") or short["iv"])
        long_delta, _= _bs_greeks(S, long_K, T, r, long_iv, opt_type)
        long_mid     = _mid(long_row)

        credit       = max(short["mid"] - long_mid, 0.01)
        actual_width = abs(short["strike"] - long_K)
        max_loss     = max(actual_width - credit, 0.01)

        # Enforce minimum 1:3 risk/reward
        if credit < actual_width / MIN_RR_DENOMINATOR:
            return None

        breakeven = (short["strike"] - credit) if opt_type == "put" \
                    else (short["strike"] + credit)

        label = "Bull Put Spread" if opt_type == "put" else "Bear Call Spread"
        return {
            "type":         label,
            "short_strike": short["strike"],
            "long_strike":  long_K,
            "short_delta":  short["delta"],
            "theta":        short["theta"],
            "iv":           short["iv"],
            "credit":       round(credit, 2),
            "max_profit":   round(credit * 100, 2),
            "max_loss":     round(max_loss * 100, 2),
            "breakeven":    round(breakeven, 2),
        }

    # ------------------------------------------------------------------
    # Individual stock options (30–45 DTE credit spreads)
    # ------------------------------------------------------------------

    def get_stock_option(self, ticker: str, direction: str,
                         confidence: float | None = None) -> dict | None:
        """
        Builds a credit spread for an individual stock:
          Bullish → Bull Put Spread  (sell OTM put, buy lower put)
          Bearish → Bear Call Spread (sell OTM call, buy higher call)

        Targets the ~30–45 DTE monthly expiry and 0.25–0.35 delta short strike.
        Returns None if the ticker has no listed options or data is insufficient.
        """
        try:
            stock = yf.Ticker(ticker)
            exps  = stock.options
            if not exps:
                logger.debug("No listed options for %s — skipping.", ticker)
                return None

            S = float(stock.fast_info.get("lastPrice") or 0)
            if S <= 0:
                return None

            # Find expiry closest to 38 DTE
            target_date = date.today() + timedelta(days=38)
            expiry_str  = min(exps, key=lambda e: abs(
                (date.fromisoformat(e) - target_date).days))
            days_out    = max((date.fromisoformat(expiry_str) - date.today()).days, 1)
            T           = days_out / 365.0

            chain    = stock.option_chain(expiry_str)
            opt_type = "put" if direction == "Bullish" else "call"
            df       = chain.puts if opt_type == "put" else chain.calls

            lo_d, hi_d = TARGET_DELTA_STOCK
            r = RISK_FREE_RATE
            candidates: list[dict] = []

            for _, row in df.iterrows():
                K  = float(row["strike"])
                iv = float(row.get("impliedVolatility") or 0)
                if iv <= 0:
                    continue
                delta, theta = _bs_greeks(S, K, T, r, iv, opt_type)
                if lo_d <= abs(delta) <= hi_d:
                    candidates.append({
                        "strike": K, "delta": round(delta, 3),
                        "theta": round(theta, 5), "iv": round(iv, 2),
                        "mid": _mid(row),
                    })

            if not candidates:
                return None

            mid_target = (lo_d + hi_d) / 2
            short      = min(candidates, key=lambda c: abs(abs(c["delta"]) - mid_target))

            # Spread width ≈ 5% of stock price, snapped to nearest $5 interval (min $5)
            raw_w      = max(round(S * 0.05 / 5) * 5, 5)
            long_K_tgt = short["strike"] - raw_w if opt_type == "put" \
                         else short["strike"] + raw_w

            df2 = df.copy()
            df2["_dist"] = abs(df2["strike"] - long_K_tgt)
            long_row  = df2.nsmallest(1, "_dist").iloc[0]
            long_K    = float(long_row["strike"])
            long_iv   = float(long_row.get("impliedVolatility") or short["iv"])
            long_delta, _ = _bs_greeks(S, long_K, T, r, long_iv, opt_type)
            long_mid  = _mid(long_row)

            credit       = max(short["mid"] - long_mid, 0.01)
            actual_width = abs(short["strike"] - long_K)
            max_loss     = max(actual_width - credit, 0.01)
            breakeven    = (short["strike"] - credit) if opt_type == "put" \
                           else (short["strike"] + credit)
            strategy     = "Bull Put Spread" if opt_type == "put" else "Bear Call Spread"

            return {
                "ticker":       ticker,
                "direction":    direction,
                "confidence":   confidence,
                "strategy":     strategy,
                "spot_price":   round(S, 2),
                "short_strike": short["strike"],
                "long_strike":  long_K,
                "expiry":       expiry_str,
                "days":         days_out,
                "credit":       round(credit, 2),
                "max_profit":   round(credit * 100, 2),
                "max_loss":     round(max_loss * 100, 2),
                "breakeven":    round(breakeven, 2),
                "delta":        short["delta"],
                "theta":        short["theta"],
                "iv":           short["iv"],
            }

        except Exception:
            logger.warning("get_stock_option failed for %s", ticker, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Report orchestrator
    # ------------------------------------------------------------------

    def build_report(self, bullish_tickers: list[str],
                     bearish_tickers: list[str]) -> dict:
        """
        Returns the full data payload for the Daily Options Brief:
          - market context (SPX, VIX)
          - 0DTE SPY iron condor setup
          - individual stock credit spreads
        """
        ctx = self.get_market_context()
        vix = ctx["vix"] or 15.0

        logger.info("Building 0DTE SPX setup (SPY proxy, VIX=%.1f)...", vix)
        spx_setup = self.build_0dte_spx_setup(vix)

        stock_options: list[dict] = []
        for t in bullish_tickers:
            opt = self.get_stock_option(t, "Bullish")
            if opt:
                stock_options.append(opt)
        for t in bearish_tickers:
            opt = self.get_stock_option(t, "Bearish")
            if opt:
                stock_options.append(opt)

        logger.info(
            "Options report built: 0DTE=%s, stocks=%d",
            "OK" if spx_setup else "N/A",
            len(stock_options),
        )
        return {
            "scan_date":     date.today().strftime("%Y-%m-%d"),
            "spx_price":     ctx["spx_price"],
            "vix":           vix,
            "spx_setup":     spx_setup,
            "stock_options": stock_options,
        }
