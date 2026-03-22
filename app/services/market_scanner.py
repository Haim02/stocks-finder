"""
Market Scanner — aggregates options trade candidates from multiple sources.

Sources:
  Finviz  : Top Gainers, Top Losers, RSI Overbought (>70), RSI Oversold (<30)
            All filtered to Optionable=True stocks only.
  TradingView : 1-Day Strong Buy / Strong Sell via tradingview-screener API.

Liquidity Guard:
  Discards any ticker whose nearest ATM option has a bid/ask spread > 10 % of mid.
"""
import logging
from dataclasses import dataclass, field

import yfinance as yf

from app.services.screener_service import ScreenerService

logger = logging.getLogger(__name__)

# ── Finviz screener URLs ──────────────────────────────────────────────────────
_BASE = "https://finviz.com/screener.ashx?v=211&ft=4"
# an_optionshort = "Has options" filter
_GAINERS_URL    = f"{_BASE}&f=an_optionshort&o=-change"
_LOSERS_URL     = f"{_BASE}&f=an_optionshort&o=change"
_OVERBOUGHT_URL = f"{_BASE}&f=an_optionshort,ta_rsi_ob70"
_OVERSOLD_URL   = f"{_BASE}&f=an_optionshort,ta_rsi_os30"


@dataclass
class ScanResult:
    ticker:              str
    source:              str    # "gainers" | "losers" | "overbought" | "oversold" | "tv_1d"
    signal:              str    # "bullish" | "bearish"
    strength:            str = "moderate"   # "strong" | "moderate"
    bid_ask_ok:          bool  = True
    bid_ask_spread_pct:  float = 0.0


class MarketScanner:
    """Aggregate options trade candidates from Finviz + TradingView."""

    # ── Finviz sources ────────────────────────────────────────────────────────

    @staticmethod
    def get_gainers(n: int = 20) -> list[ScanResult]:
        """Top % gainers today with options (bullish momentum)."""
        try:
            tickers = ScreenerService.get_candidates_from_url(_GAINERS_URL, limit=n)
            return [ScanResult(t, "gainers", "bullish", "moderate") for t in tickers]
        except Exception as e:
            logger.debug("get_gainers failed: %s", e)
            return []

    @staticmethod
    def get_losers(n: int = 20) -> list[ScanResult]:
        """Top % losers today with options (bearish momentum)."""
        try:
            tickers = ScreenerService.get_candidates_from_url(_LOSERS_URL, limit=n)
            return [ScanResult(t, "losers", "bearish", "moderate") for t in tickers]
        except Exception as e:
            logger.debug("get_losers failed: %s", e)
            return []

    @staticmethod
    def get_overbought(n: int = 20) -> list[ScanResult]:
        """RSI > 70 + optionable — bearish fade / bear call spread candidates."""
        try:
            tickers = ScreenerService.get_candidates_from_url(_OVERBOUGHT_URL, limit=n)
            return [ScanResult(t, "overbought", "bearish", "strong") for t in tickers]
        except Exception as e:
            logger.debug("get_overbought failed: %s", e)
            return []

    @staticmethod
    def get_oversold(n: int = 20) -> list[ScanResult]:
        """RSI < 30 + optionable — bullish reversal / CSP candidates."""
        try:
            tickers = ScreenerService.get_candidates_from_url(_OVERSOLD_URL, limit=n)
            return [ScanResult(t, "oversold", "bullish", "strong") for t in tickers]
        except Exception as e:
            logger.debug("get_oversold failed: %s", e)
            return []

    # ── TradingView source ────────────────────────────────────────────────────

    @staticmethod
    def get_tradingview_signals(n: int = 20) -> list[ScanResult]:
        """
        Fetch 1-Day Strong Buy / Strong Sell signals via tradingview-screener.
        Falls back to [] on any import or API error.
        """
        try:
            from tradingview_screener import Query, Column  # type: ignore

            results: list[ScanResult] = []

            def _clean(raw: str) -> str:
                return raw.split(":")[-1] if ":" in raw else raw

            # Strong Buy (Recommend.All >= 0.5)
            try:
                _, df_buy = (
                    Query()
                    .select("name", "Recommend.All")
                    .where(Column("Recommend.All") >= 0.5)
                    .limit(n)
                    .get_scanner_data()
                )
                for _, row in df_buy.iterrows():
                    t = _clean(str(row.get("name", "")))
                    if t:
                        results.append(ScanResult(t, "tv_1d", "bullish", "strong"))
            except Exception as e:
                logger.debug("TradingView buy scan failed: %s", e)

            # Strong Sell (Recommend.All <= -0.5)
            try:
                _, df_sell = (
                    Query()
                    .select("name", "Recommend.All")
                    .where(Column("Recommend.All") <= -0.5)
                    .limit(n)
                    .get_scanner_data()
                )
                for _, row in df_sell.iterrows():
                    t = _clean(str(row.get("name", "")))
                    if t:
                        results.append(ScanResult(t, "tv_1d", "bearish", "strong"))
            except Exception as e:
                logger.debug("TradingView sell scan failed: %s", e)

            logger.info("[MarketScanner] TradingView: %d signals", len(results))
            return results

        except ImportError:
            logger.debug("tradingview_screener not available")
            return []
        except Exception as e:
            logger.debug("get_tradingview_signals failed: %s", e)
            return []

    # ── Liquidity guard ───────────────────────────────────────────────────────

    @staticmethod
    def check_liquidity(
        ticker: str, max_spread_pct: float = 0.10
    ) -> tuple[bool, float]:
        """
        Check nearest ATM option bid/ask spread.
        Returns (is_liquid, spread_pct).
        Spread > max_spread_pct → illiquid, discard.
        Fallback: (True, 0.0) so API failures never block the pipeline.
        """
        try:
            stock    = yf.Ticker(ticker)
            expiries = stock.options
            if not expiries:
                return True, 0.0
            chain = stock.option_chain(expiries[0])
            try:
                price = stock.fast_info.last_price
            except Exception:
                return True, 0.0
            if not price:
                return True, 0.0

            calls = chain.calls.copy()
            calls["dist"] = (calls["strike"] - price).abs()
            atm = calls.sort_values("dist").iloc[0]

            bid = float(atm.get("bid") or 0)
            ask = float(atm.get("ask") or 0)
            mid = (bid + ask) / 2
            if mid <= 0:
                return True, 0.0

            spread_pct = (ask - bid) / mid
            is_liquid  = spread_pct <= max_spread_pct
            if not is_liquid:
                logger.debug(
                    "[LiquidityGuard] %s: spread %.1f%% > %.0f%% — discarding",
                    ticker, spread_pct * 100, max_spread_pct * 100,
                )
            return is_liquid, round(spread_pct, 4)

        except Exception as e:
            logger.debug("check_liquidity(%s) failed: %s", ticker, e)
            return True, 0.0

    # ── Combined scan ─────────────────────────────────────────────────────────

    def full_scan(
        self,
        n_per_source:         int  = 15,
        apply_liquidity_guard: bool = True,
    ) -> tuple[list[ScanResult], list[ScanResult]]:
        """
        Run all sources, apply liquidity guard, deduplicate by ticker,
        and return (bullish_results, bearish_results).
        """
        all_results: list[ScanResult] = (
            self.get_gainers(n_per_source)
            + self.get_losers(n_per_source)
            + self.get_overbought(n_per_source)
            + self.get_oversold(n_per_source)
            + self.get_tradingview_signals(n_per_source)
        )

        if apply_liquidity_guard:
            filtered: list[ScanResult] = []
            for r in all_results:
                ok, spread = self.check_liquidity(r.ticker)
                r.bid_ask_ok         = ok
                r.bid_ask_spread_pct = spread
                if ok:
                    filtered.append(r)
                else:
                    logger.info(
                        "[LiquidityGuard] Removed %s (spread=%.1f%%)",
                        r.ticker, spread * 100,
                    )
            all_results = filtered

        # Deduplicate by ticker — keep strongest signal per direction
        seen_bull: dict[str, ScanResult] = {}
        seen_bear: dict[str, ScanResult] = {}
        for r in all_results:
            if r.signal == "bullish":
                if r.ticker not in seen_bull or r.strength == "strong":
                    seen_bull[r.ticker] = r
            else:
                if r.ticker not in seen_bear or r.strength == "strong":
                    seen_bear[r.ticker] = r

        bullish = list(seen_bull.values())
        bearish = list(seen_bear.values())
        logger.info(
            "[MarketScanner] Full scan: %d bullish, %d bearish (after liquidity guard=%s)",
            len(bullish), len(bearish), apply_liquidity_guard,
        )
        return bullish, bearish
