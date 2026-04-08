"""
Multi-strategy options engine.
Selects the optimal strategy per ticker based on IV rank, trend, RSI, and VIX.

Strategy rules (analyst-grade):
  BULLISH (green):
    bull_put_spread   — IVR > 30, RSI < 60, delta ~0.20          (credit)
    cash_secured_put  — IVR > 50, bullish, oversold RSI < 35     (credit, 30-45 DTE)
    bull_call_spread  — IVR < 25, trend strong_bullish            (debit)
    long_call_leap    — IVR < 25, strong bullish, DTE > 60        (debit, stock replacement)
    covered_call      — own shares, IVR > 30, RSI > 60           (credit)

  BEARISH (red):
    bear_call_spread  — IVR > 30, RSI > 65, delta ~0.20          (credit)
    bear_put_spread   — IVR < 25, trend bearish                   (debit)

  NEUTRAL / VOLATILITY (gray/orange):
    iron_condor       — IVR > 50, neutral, profit zone 10-15%    (credit)
    long_straddle     — IVR > 50 + earnings < 7 days             (debit)
    short_strangle    — index ETFs only, VIX > 25                 (credit, undefined risk)

Management rules:
  - TAKE PROFIT          : current P&L ≥ 50 % of max profit
  - TIME SENSITIVE       : DTE ≤ 21
  - DANGER - ADJUST      : price at or beyond a break-even level
"""
import logging
from typing import Literal, Optional

from pydantic import BaseModel

from app.services.iv_calculator import get_nearest_expiry

logger = logging.getLogger(__name__)

INDEX_ETFS: frozenset[str] = frozenset(
    {"SPY", "QQQ", "IWM", "DIA", "XLF", "XLE", "XLK", "XBI", "GLD", "TLT"}
)

TrendType      = Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
CategoryType   = Literal["BULLISH", "BEARISH", "NEUTRAL"]
ManagementStatus = Literal["OK", "TAKE PROFIT", "TIME SENSITIVE - MANAGE/ROLL", "DANGER - ADJUST"]


class StrategySignal(BaseModel):
    """Pydantic model representing a fully-defined options strategy recommendation."""

    # ── Identity ──────────────────────────────────────────────────────────────
    strategy_name:    str
    strategy_display: str
    category:         CategoryType
    ticker:           str
    underlying_price: float

    # ── Strikes (0.0 = leg not used) ─────────────────────────────────────────
    leg1_strike: float = 0.0
    leg2_strike: float = 0.0
    leg3_strike: float = 0.0
    leg4_strike: float = 0.0

    # ── P&L (dollars per contract, already × 100) ────────────────────────────
    net_credit:           float = 0.0
    net_debit:            float = 0.0
    max_profit:           float = 0.0
    max_loss:             float = 0.0
    break_even_low:       float = 0.0
    break_even_high:      float = 0.0
    probability_of_profit: float = 0.0
    risk_reward_ratio:    float = 0.0

    # ── Greeks (estimated) ───────────────────────────────────────────────────
    theta_daily:    float = 0.0   # daily time decay ($ per contract)
    vega_per_1pct:  float = 0.0   # P&L change per 1 % IV move ($ per contract)

    # ── Trade parameters ─────────────────────────────────────────────────────
    expiry_date:   str   = ""
    dte:           int   = 35
    iv_rank:       float = 0.0
    current_iv:    float = 0.0
    target_delta:  float = 0.20

    # ── Management ───────────────────────────────────────────────────────────
    close_at_profit_pct: float = 0.50
    manage_at_dte:       int   = 21
    close_target_dollar: float = 0.0

    # ── Strategy-specific extras ─────────────────────────────────────────────
    return_on_capital: float = 0.0
    annualized_return: float = 0.0
    move_needed_pct:   float = 0.0

    # Calendar Spread specific
    near_expiry: str = ""       # short-leg expiry (closer date)
    far_expiry:  str = ""       # long-leg expiry (further date)
    near_dte:    int = 0
    far_dte:     int = 0

    # Back Ratio specific
    ratio_short: int = 1        # number of short contracts
    ratio_long:  int = 2        # number of long contracts

    # Broken-Wing Butterfly specific
    is_broken_wing: bool  = False
    skip_width:     float = 0.0  # extra distance on the far wing

    # ── Capital efficiency ────────────────────────────────────────────────────
    margin_required:   float = 0.0
    capital_efficiency: str  = ""   # e.g. "🟢 מצוין"
    margin_note:       str   = ""   # human-readable explanation

    # ── Context ───────────────────────────────────────────────────────────────
    rationale:        str = ""
    market_condition: str = ""
    telegram_message: str = ""
    news_pulse:       str = ""   # populated externally from NewsScraper

    class Config:
        frozen = False


class OptionsStrategyEngine:
    """Select the best options strategy per ticker; format Telegram messages."""

    # ── Margin helper ────────────────────────────────────────────────────────

    def _apply_margin(self, signal: StrategySignal) -> StrategySignal:
        """Enrich signal with margin_required, return_on_capital, and capital_efficiency."""
        from app.services.margin_calculator import calculate_margin
        try:
            result = calculate_margin(signal)
            signal.margin_required    = result["margin"]
            signal.return_on_capital  = result["roc"]
            signal.capital_efficiency = result["label"]
            signal.margin_note        = result["note"]
        except Exception as e:
            logger.debug("_apply_margin failed for %s: %s", signal.ticker, e)
        return signal

    # ── Public: strategy selector ────────────────────────────────────────────

    def select_strategy(
        self,
        ticker:           str,
        price:            float,
        trend:            TrendType,
        iv_rank:          float,
        rsi:              float,
        vix_level:        float,
        has_earnings_soon: bool = False,
        dte_preference:   int  = 35,
        owns_shares:      bool = False,
        gex_regime:       str  = "unknown",
    ) -> Optional[StrategySignal]:
        """
        Return the optimal StrategySignal, or None if no edge is detected.

        gex_regime: optional pre-computed GEX regime ("positive" | "negative" |
                    "transitional" | "unknown"). When "negative", premium-selling
                    strategies are skipped — the market is in vol-expansion mode.

        Priority order (top wins):
          1. Earnings straddle
          2. Iron Condor (neutral + high IV)
          3. Bear Call Spread (overbought + high IV)
          4. Bull Put Spread (bullish + IVR > 30 + RSI < 60)
          5. Cash-Secured Put (oversold + high IV)
          6. Covered Call (own shares)
          7. Short Strangle (index ETF + VIX spike)
          8. Bull Call Spread (low IV + bullish)  ← NOT blocked by negative GEX
          9. Long Call LEAP (low IV + strong bullish + long DTE)
         10. Bear Put Spread (low IV + bearish)
        """
        kw = dict(ticker=ticker, price=price, iv_rank=iv_rank, dte=dte_preference)
        neg_gex = (gex_regime == "negative")   # block premium selling if True

        if has_earnings_soon and iv_rank > 50:
            s = self._build_long_straddle(**kw)
            s.rationale = "עסקת דוחות — צפויה תנועה חדה, כיוון לא ידוע"
            return self._apply_margin(s)

        if iv_rank >= 35 and trend == "neutral" and not neg_gex:
            s = self._build_iron_condor(**kw)
            s.rationale = "IVR גבוה + שוק ניטרלי — גביית פרמיה משני הצדדים (אזור רווח 10-15%)"
            return self._apply_margin(s)

        if iv_rank > 30 and trend in ("neutral", "bearish", "strong_bearish") and rsi > 65 and not neg_gex:
            s = self._build_bear_call_spread(**kw)
            s.rationale = "IVR גבוה + RSI קניית יתר (>65) — מכירת Call Spread מעל התנגדות, ~0.20 דלתא"
            return self._apply_margin(s)

        # Butterfly: high precision pin at expiry (more specific than bull_put_spread)
        if iv_rank > 40 and trend == "neutral" and 44 <= rsi <= 56 and dte_preference <= 21:
            s = self._build_butterfly(ticker, price, iv_rank, dte_preference)
            s.rationale = "מניה תקועה + IV גבוה + קרוב לפקיעה — דיוק מקסימלי ב-Butterfly"
            return self._apply_margin(s)

        # Broken-Wing Butterfly: medium IV + bullish/neutral + medium DTE
        if 30 <= iv_rank <= 55 and trend in ("bullish", "neutral") and 21 <= dte_preference <= 45:
            s = self._build_broken_wing_butterfly(ticker, price, iv_rank, dte_preference)
            s.rationale = "IV בינוני + נטייה שורית — מבנה א-סימטרי עם קרדיט נטו"
            return self._apply_margin(s)

        if iv_rank >= 25 and trend in ("bullish", "neutral") and rsi < 60 and not neg_gex:
            s = self._build_bull_put_spread(**kw)
            s.rationale = "IVR > 25 + נטייה שורית + RSI < 60 — קרדיט מתחת לתמיכה, ~0.20 דלתא, PoP 68%"
            return self._apply_margin(s)

        if iv_rank > 50 and trend in ("bullish", "strong_bullish") and rsi < 35 and not neg_gex:
            s = self._build_cash_secured_put(**kw)
            s.rationale = "IVR גבוה + מכירת יתר (RSI < 35) + שורי — להיכנס לירידה תוך גביית פרמיה, 30-45 DTE"
            return self._apply_margin(s)

        if owns_shares and iv_rank > 30 and rsi > 60 and not neg_gex:
            s = self._build_covered_call(**kw)
            s.rationale = "מחזיק מניות + IVR מוגבר + ליד התנגדות — יצירת הכנסה חודשית שוטפת"
            return self._apply_margin(s)

        if vix_level > 25 and iv_rank > 60 and ticker in INDEX_ETFS and not neg_gex:
            s = self._build_short_strangle(**kw)
            s.rationale = "זינוק VIX + ETF מדד — מכירת פרמיית תנודתיות גבוהה (סיכון בלתי מוגבל, השתמש בסטופים)"
            return self._apply_margin(s)

        # Call Back Ratio: strong bullish + low IV + expecting big explosive move up
        if iv_rank < 25 and trend == "strong_bullish" and 30 <= dte_preference <= 60:
            s = self._build_call_back_ratio(ticker, price, iv_rank, dte_preference)
            s.rationale = "IV נמוך + זינוק שורי חזק צפוי — חשיפה בלתי מוגבלת בעלות אפס"
            return self._apply_margin(s)

        if iv_rank < 25 and trend in ("bullish", "strong_bullish"):
            s = self._build_bull_call_spread(**kw)
            s.rationale = "IVR נמוך + שורי — ספרד דביט זול, סיכון מוגדר, משחק כיווני"
            return self._apply_margin(s)

        if iv_rank < 25 and trend == "strong_bullish" and dte_preference > 60:
            s = self._build_long_call_leap(**kw)
            s.rationale = "IVR נמוך + מגמה שורית חזקה — קולים זולים לטווח ארוך כתחליף מניה"
            return self._apply_margin(s)

        if iv_rank < 25 and trend in ("bearish", "strong_bearish"):
            s = self._build_bear_put_spread(**kw)
            s.rationale = "IVR נמוך + דובי — Put ספרד בדביט, סיכון מוגדר, משחק כיווני"
            return self._apply_margin(s)

        # Calendar Spread: low IV + truly neutral + enough time
        if iv_rank < 30 and trend == "neutral" and dte_preference >= 45:
            s = self._build_calendar_spread(ticker, price, iv_rank, dte_preference)
            s.rationale = "IV נמוך + מניה תקועה — מרוויחים מהבדל שחיקת הזמן בין פקיעות"
            return self._apply_margin(s)

        return None

    # ── Public: management monitor ───────────────────────────────────────────

    def check_management_status(
        self,
        signal:              StrategySignal,
        current_price:       float,
        current_dte:         int,
        current_pnl_dollar:  float = 0.0,
    ) -> ManagementStatus:
        """
        Evaluate a live position and return its management status.
          TAKE PROFIT          → P&L ≥ 50 % of max profit
          TIME SENSITIVE       → DTE ≤ manage_at_dte (default 21)
          DANGER - ADJUST      → price at or beyond a break-even
          OK                   → no action needed
        """
        if signal.max_profit > 0 and current_pnl_dollar >= signal.max_profit * signal.close_at_profit_pct:
            return "TAKE PROFIT"
        if current_dte <= signal.manage_at_dte:
            return "TIME SENSITIVE - MANAGE/ROLL"
        if signal.break_even_low > 0 and current_price <= signal.break_even_low:
            return "DANGER - ADJUST"
        if signal.break_even_high > 0 and current_price >= signal.break_even_high:
            return "DANGER - ADJUST"
        return "OK"

    # ── Expiry + strike helpers ───────────────────────────────────────────────

    @staticmethod
    def get_real_expiration(ticker: str, target_dte: int = 35) -> str:
        """Fetch the real option expiration closest to target_dte from yfinance."""
        try:
            import yfinance as yf
            from datetime import datetime, timedelta
            exps   = yf.Ticker(ticker).options
            if not exps:
                return (datetime.now() + timedelta(days=target_dte)).strftime("%Y-%m-%d")
            target = datetime.now() + timedelta(days=target_dte)
            return min(exps, key=lambda x: abs(datetime.strptime(x, "%Y-%m-%d") - target))
        except Exception:
            from datetime import datetime, timedelta
            return (datetime.now() + timedelta(days=target_dte)).strftime("%Y-%m-%d")

    @staticmethod
    def get_two_sigma_strikes(price: float, iv_rank: float, trend: str) -> tuple:
        """
        Two Sigma probability-based strike selection at 1.5-2.0 standard deviations.
        Returns: (short_put, long_put, short_call, long_call)
        """
        # OTM% scales linearly with IV rank: 6% at IVR=0, 11% at IVR=100
        # Higher IV → wider strikes → higher PoP, less premium
        otm_pct       = 0.06 + (iv_rank / 100) * 0.05
        expected_move = price * otm_pct
        wing          = max(price * 0.05, 5)

        short_put  = round((price - expected_move) / 0.5) * 0.5
        long_put   = round((short_put - wing)       / 0.5) * 0.5
        short_call = round((price + expected_move)  / 0.5) * 0.5
        long_call  = round((short_call + wing)      / 0.5) * 0.5
        return short_put, long_put, short_call, long_call

    # ── Strategy builders ─────────────────────────────────────────────────────

    def _build_iron_condor(
        self, ticker, price, iv_rank, dte,
        upper_bb: float = 0.0, lower_bb: float = 0.0,
    ) -> StrategySignal:
        """
        Iron Condor — uses real market data when available, falls back to theoretical.
        When upper_bb/lower_bb are provided, aligns short strikes with Bollinger Bands.
        """
        from app.services.iv_calculator import get_real_spread_data, get_nearest_expiry

        real = get_real_spread_data(ticker, dte, "iron_condor")

        if real and real.get("net_credit", 0) > 0:
            sp       = real["put_short"]
            lp       = real["put_long"]
            sc       = real["call_short"]
            lc       = real["call_long"]
            credit   = real["net_credit"]
            mp       = real["max_profit"]
            ml       = real["max_loss"]
            be_l     = real["be_low"]
            be_h     = real["be_high"]
            expiry   = real["expiry"]
            real_dte = real["dte"]
            iv_note  = " (BB)" if upper_bb > 0 else ""
        else:
            # Use BB levels for short strikes when available
            if upper_bb > 0 and lower_bb > 0:
                sp = round(lower_bb * 0.99)   # just below lower BB
                sc = round(upper_bb * 1.01)   # just above upper BB
                lp = round(sp * 0.96)         # wing below short put
                lc = round(sc * 1.04)         # wing above short call
                iv_note = " (BB תיאורטי)"
            else:
                # Two Sigma probability-based strikes
                sp, lp, sc, lc = self.get_two_sigma_strikes(price, iv_rank, "neutral")
                iv_note = " (2σ תיאורטי)"
            wing   = sp - lp
            credit = round(wing * 0.38, 2)
            mp     = round(credit * 100, 2)
            ml     = round((wing - credit) * 100, 2)
            be_l   = round(sp - credit, 2)
            be_h   = round(sc + credit, 2)
            expiry = get_nearest_expiry(ticker, dte)
            real_dte = dte

        pz  = (be_h - be_l) / price * 100
        pop = min(75.0, 50 + pz * 1.2)
        rr  = round(mp / ml, 2) if ml > 0 else 0

        return StrategySignal(
            strategy_name="iron_condor", strategy_display=f"Iron Condor 🦅{iv_note}",
            category="NEUTRAL", ticker=ticker, underlying_price=price,
            leg1_strike=sp, leg2_strike=lp, leg3_strike=sc, leg4_strike=lc,
            net_credit=credit, max_profit=mp, max_loss=ml,
            break_even_low=be_l, break_even_high=be_h,
            probability_of_profit=round(pop, 1), risk_reward_ratio=rr,
            target_delta=0.15,
            expiry_date=expiry, dte=real_dte, iv_rank=iv_rank,
            close_target_dollar=round(credit * 0.50 * 100, 2), manage_at_dte=21,
        )

    def _build_bull_put_spread(self, ticker, price, iv_rank, dte) -> StrategySignal:
        """Bull Put Spread — uses real market data when available, falls back to theoretical."""
        from app.services.iv_calculator import get_real_spread_data, get_nearest_expiry

        real = get_real_spread_data(ticker, dte, "bull_put_spread")

        if real and real.get("net_credit", 0) > 0:
            sp       = real["short_strike"]
            lp       = real["long_strike"]
            credit   = real["net_credit"]
            mp       = real["max_profit"]
            ml       = real["max_loss"]
            be       = real["break_even"]
            expiry   = real["expiry"]
            real_dte = real["dte"]
            rr       = real.get("rr", round(mp / ml, 2) if ml > 0 else 0)
            iv_note  = f" (IV: {real.get('short_iv', 0):.0f}%)" if real.get("short_iv") else ""
        else:
            sp = round(price * 0.95); lp = round(price * 0.90)
            width  = sp - lp
            credit = round(width * 0.40, 2)
            mp     = round(credit * 100, 2)
            ml     = round((width - credit) * 100, 2)
            be     = round(sp - credit, 2)
            expiry = get_nearest_expiry(ticker, dte)
            real_dte = dte
            rr     = round(mp / ml, 2) if ml > 0 else 0
            iv_note = " (תיאורטי)"

        return StrategySignal(
            strategy_name="bull_put_spread", strategy_display=f"Bull Put Spread 🐂{iv_note}",
            category="BULLISH", ticker=ticker, underlying_price=price,
            leg1_strike=sp, leg2_strike=lp,
            net_credit=credit, max_profit=mp, max_loss=ml,
            break_even_low=be, break_even_high=round(price * 1.20, 2),
            probability_of_profit=68.0, risk_reward_ratio=rr,
            target_delta=0.20,
            expiry_date=expiry, dte=real_dte, iv_rank=iv_rank,
            close_target_dollar=round(credit * 0.50 * 100, 2), manage_at_dte=21,
        )

    def _build_bear_call_spread(self, ticker, price, iv_rank, dte) -> StrategySignal:
        """Bear Call Spread — uses real market data when available, falls back to theoretical."""
        from app.services.iv_calculator import get_real_spread_data, get_nearest_expiry

        real = get_real_spread_data(ticker, dte, "bear_call_spread")

        if real and real.get("net_credit", 0) > 0:
            sc       = real["short_strike"]
            lc       = real["long_strike"]
            credit   = real["net_credit"]
            mp       = real["max_profit"]
            ml       = real["max_loss"]
            be       = real["break_even"]
            expiry   = real["expiry"]
            real_dte = real["dte"]
            rr       = real.get("rr", round(mp / ml, 2) if ml > 0 else 0)
            iv_note  = ""
        else:
            sc = round(price * 1.05); lc = round(price * 1.10)
            width  = lc - sc
            credit = round(width * 0.40, 2)
            mp     = round(credit * 100, 2)
            ml     = round((width - credit) * 100, 2)
            be     = round(sc + credit, 2)
            expiry = get_nearest_expiry(ticker, dte)
            real_dte = dte
            rr     = round(mp / ml, 2) if ml > 0 else 0
            iv_note = " (תיאורטי)"

        return StrategySignal(
            strategy_name="bear_call_spread", strategy_display=f"Bear Call Spread 🐻{iv_note}",
            category="BEARISH", ticker=ticker, underlying_price=price,
            leg1_strike=sc, leg2_strike=lc,
            net_credit=credit, max_profit=mp, max_loss=ml,
            break_even_low=round(price * 0.80, 2), break_even_high=be,
            probability_of_profit=68.0, risk_reward_ratio=rr,
            target_delta=0.20,
            expiry_date=expiry, dte=real_dte, iv_rank=iv_rank,
            close_target_dollar=round(credit * 0.50 * 100, 2), manage_at_dte=21,
        )

    def _build_cash_secured_put(self, ticker, price, iv_rank, dte) -> StrategySignal:
        """Cash-Secured Put — uses real market data when available, falls back to theoretical."""
        from app.services.iv_calculator import get_real_option_data, get_nearest_expiry

        dte_use = max(dte, 30)
        real = get_real_option_data(ticker, dte_use, target_delta=0.30, option_type="put")

        if real and real.get("mark", 0) > 0:
            strike   = real["strike"]
            premium  = real["mark"]
            expiry   = real["expiry"]
            real_dte = real["dte"]
            iv_note  = f" (IV: {real.get('iv', 0):.0f}%)"
        else:
            strike   = round(price * 0.95)
            iv       = max(iv_rank / 100, 0.20)
            premium  = round(strike * iv * 0.30 * (dte_use / 365) ** 0.5, 2)
            expiry   = get_nearest_expiry(ticker, dte_use)
            real_dte = dte_use
            iv_note  = " (תיאורטי)"

        mp  = round(premium * 100, 2)
        ml  = round((strike - premium) * 100, 2)
        be  = round(strike - premium, 2)
        roc = round((premium / strike) * 100, 2)
        ann = round(roc * (365 / max(real_dte, 1)), 2)

        return StrategySignal(
            strategy_name="cash_secured_put", strategy_display=f"Cash-Secured Put 💵{iv_note}",
            category="BULLISH", ticker=ticker, underlying_price=price,
            leg1_strike=strike,
            net_credit=premium, max_profit=mp, max_loss=ml,
            break_even_low=be, break_even_high=float(strike),
            probability_of_profit=70.0,
            target_delta=0.20,
            expiry_date=expiry, dte=real_dte, iv_rank=iv_rank,
            close_target_dollar=round(premium * 0.50 * 100, 2), manage_at_dte=21,
            return_on_capital=roc, annualized_return=ann,
        )

    def _build_covered_call(self, ticker, price, iv_rank, dte) -> StrategySignal:
        strike  = round(price * 1.05)
        iv      = max(iv_rank / 100, 0.20)
        premium = price * iv * 0.25 * (dte / 365) ** 0.5
        mp      = (strike - price + premium) * 100
        ml      = (price - premium) * 100
        be      = price - premium
        roc     = (premium / price) * 100
        ann     = roc * (365 / dte) if dte else 0
        theta   = premium * 100 / (dte * 2) if dte else 0
        exp     = get_nearest_expiry(ticker, dte)
        return StrategySignal(
            strategy_name="covered_call", strategy_display="Covered Call 📞",
            category="BULLISH", ticker=ticker, underlying_price=price,
            leg1_strike=strike,
            net_credit=round(premium, 2), max_profit=round(mp, 2), max_loss=round(ml, 2),
            break_even_low=round(be, 2), break_even_high=round(strike, 2),
            probability_of_profit=70.0,
            theta_daily=round(theta, 2), vega_per_1pct=round(-ml / 80, 2),
            expiry_date=exp, dte=dte, iv_rank=iv_rank,
            close_target_dollar=round(premium * 0.50 * 100, 2), manage_at_dte=21,
            return_on_capital=round(roc, 2), annualized_return=round(ann, 2),
        )

    def _build_bull_call_spread(self, ticker, price, iv_rank, dte) -> StrategySignal:
        lc    = round(price)           # buy ATM
        sc    = round(price * 1.08)    # sell OTM
        width = sc - lc
        debit = width * 0.45
        mp    = (width - debit) * 100
        ml    = debit * 100
        be    = lc + debit
        rr    = mp / ml if ml else 0
        theta = -ml / (dte * 3) if dte else 0
        exp   = get_nearest_expiry(ticker, dte)
        return StrategySignal(
            strategy_name="bull_call_spread", strategy_display="Bull Call Spread 🐂",
            category="BULLISH", ticker=ticker, underlying_price=price,
            leg1_strike=lc, leg2_strike=sc,
            net_debit=round(debit, 2), max_profit=round(mp, 2), max_loss=round(ml, 2),
            break_even_low=round(be, 2), break_even_high=round(sc, 2),
            probability_of_profit=47.0, risk_reward_ratio=round(rr, 2),
            theta_daily=round(theta, 2), vega_per_1pct=round(ml / 80, 2),
            expiry_date=exp, dte=dte, iv_rank=iv_rank,
            close_target_dollar=round(mp * 0.50, 2), manage_at_dte=21,
        )

    def _build_bear_put_spread(self, ticker, price, iv_rank, dte) -> StrategySignal:
        lp    = round(price)           # buy ATM
        sp    = round(price * 0.92)    # sell OTM
        width = lp - sp
        debit = width * 0.45
        mp    = (width - debit) * 100
        ml    = debit * 100
        be    = lp - debit
        rr    = mp / ml if ml else 0
        theta = -ml / (dte * 3) if dte else 0
        exp   = get_nearest_expiry(ticker, dte)
        return StrategySignal(
            strategy_name="bear_put_spread", strategy_display="Bear Put Spread 🐻",
            category="BEARISH", ticker=ticker, underlying_price=price,
            leg1_strike=lp, leg2_strike=sp,
            net_debit=round(debit, 2), max_profit=round(mp, 2), max_loss=round(ml, 2),
            break_even_low=round(sp, 2), break_even_high=round(be, 2),
            probability_of_profit=47.0, risk_reward_ratio=round(rr, 2),
            theta_daily=round(theta, 2), vega_per_1pct=round(ml / 80, 2),
            expiry_date=exp, dte=dte, iv_rank=iv_rank,
            close_target_dollar=round(mp * 0.50, 2), manage_at_dte=21,
        )

    def _build_long_straddle(self, ticker, price, iv_rank, dte) -> StrategySignal:
        strike    = round(price)
        iv        = max(iv_rank / 100, 0.25)
        dte_use   = min(dte, 7)   # earnings play — short dated
        prem_each = price * iv * 0.40 * (dte_use / 365) ** 0.5
        total     = prem_each * 2
        ml        = total * 100
        be_h      = strike + total
        be_l      = strike - total
        move_pct  = (total / price) * 100
        theta     = -ml / (dte_use * 2) if dte_use else 0
        exp       = get_nearest_expiry(ticker, dte_use)
        return StrategySignal(
            strategy_name="long_straddle", strategy_display="Long Straddle ⚡",
            category="NEUTRAL", ticker=ticker, underlying_price=price,
            leg1_strike=strike, leg2_strike=strike,
            net_debit=round(total, 2), max_profit=9_999_999.0, max_loss=round(ml, 2),
            break_even_low=round(be_l, 2), break_even_high=round(be_h, 2),
            probability_of_profit=35.0,
            theta_daily=round(theta, 2), vega_per_1pct=round(ml / 40, 2),
            expiry_date=exp, dte=dte_use, iv_rank=iv_rank,
            close_target_dollar=round(ml * 0.50, 2), manage_at_dte=2,
            move_needed_pct=round(move_pct, 1),
        )

    def _build_long_call_leap(self, ticker, price, iv_rank, dte) -> StrategySignal:
        strike  = round(price * 0.85)   # deep ITM ~0.75 delta
        iv      = max(iv_rank / 100, 0.20)
        dte_use = max(dte, 180)
        premium = (price - strike) + price * iv * 0.20 * (dte_use / 365) ** 0.5
        ml      = premium * 100
        be      = strike + premium
        theta   = -ml / (dte_use * 4) if dte_use else 0
        exp     = get_nearest_expiry(ticker, dte_use)
        return StrategySignal(
            strategy_name="long_call_leap", strategy_display="Long Call LEAP 🚀",
            category="BULLISH", ticker=ticker, underlying_price=price,
            leg1_strike=strike,
            net_debit=round(premium, 2), max_profit=9_999_999.0, max_loss=round(ml, 2),
            break_even_low=round(be, 2), break_even_high=9_999_999.0,
            probability_of_profit=65.0,
            theta_daily=round(theta, 2), vega_per_1pct=round(ml / 60, 2),
            expiry_date=exp, dte=dte_use, iv_rank=iv_rank,
            close_target_dollar=round(ml * 0.50, 2), manage_at_dte=60,
        )

    def _build_short_strangle(self, ticker, price, iv_rank, dte) -> StrategySignal:
        sp     = round(price * 0.93)
        sc     = round(price * 1.07)
        iv     = max(iv_rank / 100, 0.25)
        prem   = price * iv * 0.20 * (dte / 365) ** 0.5
        credit = prem * 2
        mp     = credit * 100
        be_l   = sp - credit
        be_h   = sc + credit
        theta  = mp / dte if dte else 0
        exp    = get_nearest_expiry(ticker, dte)
        return StrategySignal(
            strategy_name="short_strangle", strategy_display="Short Strangle ⚠️",
            category="NEUTRAL", ticker=ticker, underlying_price=price,
            leg1_strike=sp, leg2_strike=sc,
            net_credit=round(credit, 2), max_profit=round(mp, 2), max_loss=9_999_999.0,
            break_even_low=round(be_l, 2), break_even_high=round(be_h, 2),
            probability_of_profit=68.0,
            theta_daily=round(theta, 2), vega_per_1pct=round(-mp / 30, 2),
            expiry_date=exp, dte=dte, iv_rank=iv_rank,
            close_target_dollar=round(credit * 0.50 * 100, 2), manage_at_dte=21,
        )

    def _build_calendar_spread(self, ticker: str, price: float, iv_rank: float, dte: int) -> StrategySignal:
        """Calendar Spread: Sell near-term ATM + Buy far-term ATM. Profits from theta differential."""
        from app.services.iv_calculator import get_nearest_expiry
        strike   = round(price)
        near_exp = get_nearest_expiry(ticker, 30)
        far_exp  = get_nearest_expiry(ticker, 60)
        debit    = round(price * 0.02, 2)
        mp       = round(debit * 1.5 * 100, 2)
        ml       = round(debit * 100, 2)
        be_l     = round(strike * 0.96, 2)
        be_h     = round(strike * 1.04, 2)
        return StrategySignal(
            strategy_name="calendar_spread",
            strategy_display="Calendar Spread 📅",
            category="NEUTRAL",
            ticker=ticker,
            underlying_price=price,
            leg1_strike=float(strike),
            leg2_strike=float(strike),
            net_debit=debit,
            max_profit=mp,
            max_loss=ml,
            break_even_low=be_l,
            break_even_high=be_h,
            probability_of_profit=55.0,
            risk_reward_ratio=round(mp / ml, 2) if ml > 0 else 0,
            expiry_date=near_exp,
            dte=30,
            iv_rank=iv_rank,
            near_expiry=near_exp,
            far_expiry=far_exp,
            near_dte=30,
            far_dte=60,
            close_at_profit_pct=0.25,
            manage_at_dte=23,
            close_target_dollar=round(debit * 0.25 * 100, 2),
        )

    def _build_butterfly(self, ticker: str, price: float, iv_rank: float, dte: int) -> StrategySignal:
        """Butterfly: Buy low + Sell 2 ATM + Buy high. Max profit when stock pins at middle strike."""
        from app.services.iv_calculator import get_nearest_expiry
        sl    = round(price * 0.95)
        sm    = round(price)
        sh    = round(price * 1.05)
        wing  = sm - sl
        debit = round(wing * 0.25, 2)
        mp    = round((wing - debit) * 100, 2)
        ml    = round(debit * 100, 2)
        be_l  = round(sl + debit, 2)
        be_h  = round(sh - debit, 2)
        exp   = get_nearest_expiry(ticker, min(dte, 21))
        return StrategySignal(
            strategy_name="butterfly",
            strategy_display="Butterfly 🦋",
            category="NEUTRAL",
            ticker=ticker,
            underlying_price=price,
            leg1_strike=float(sl),
            leg2_strike=float(sm),
            leg3_strike=float(sh),
            net_debit=debit,
            max_profit=mp,
            max_loss=ml,
            break_even_low=be_l,
            break_even_high=be_h,
            probability_of_profit=30.0,
            risk_reward_ratio=round(mp / ml, 2) if ml > 0 else 0,
            expiry_date=exp,
            dte=min(dte, 21),
            iv_rank=iv_rank,
            close_at_profit_pct=0.50,
            manage_at_dte=7,
            close_target_dollar=round(mp * 0.50, 2),
        )

    def _build_call_back_ratio(self, ticker: str, price: float, iv_rank: float, dte: int) -> StrategySignal:
        """Call Back Ratio 1x2: Sell 1 ATM Call + Buy 2 OTM Calls. Unlimited profit above upper strike."""
        from app.services.iv_calculator import get_nearest_expiry
        iv         = max(iv_rank / 100, 0.20)
        ss         = round(price)               # short strike (ATM)
        sl         = round(price * 1.05)        # long strike (OTM)
        width      = sl - ss
        prem_short = price * iv * 0.3 * (dte / 365) ** 0.5
        prem_long  = prem_short * 0.60
        net        = (prem_long * 2) - prem_short

        if net >= 0:
            net_debit  = round(net, 2)
            net_credit = 0.0
        else:
            net_debit  = 0.0
            net_credit = round(abs(net), 2)

        max_loss = round((width - net_credit + net_debit) * 100, 2)
        be_high  = round(sl + max_loss / 100, 2)
        exp      = get_nearest_expiry(ticker, dte)
        return StrategySignal(
            strategy_name="call_back_ratio",
            strategy_display="Call Back Ratio 1×2 🚀",
            category="BULLISH",
            ticker=ticker,
            underlying_price=price,
            leg1_strike=float(ss),
            leg2_strike=float(sl),
            net_debit=net_debit,
            net_credit=net_credit,
            max_profit=9_999_999.0,
            max_loss=max_loss,
            break_even_low=float(ss),
            break_even_high=be_high,
            probability_of_profit=40.0,
            risk_reward_ratio=0.0,
            expiry_date=exp,
            dte=dte,
            iv_rank=iv_rank,
            ratio_short=1,
            ratio_long=2,
            close_at_profit_pct=0.50,
            manage_at_dte=21,
            close_target_dollar=round(max_loss * 0.50, 2),
        )

    def _build_broken_wing_butterfly(self, ticker: str, price: float, iv_rank: float, dte: int) -> StrategySignal:
        """Broken-Wing Butterfly (Put): asymmetric structure, bullish skew, net credit or zero cost."""
        from app.services.iv_calculator import get_nearest_expiry
        sl   = round(price * 0.90)   # low put
        sm   = round(price * 0.95)   # mid put (short x2)
        sh   = round(price * 1.02)   # high put (broken wing — wider)

        lower_wing = sm - sl
        upper_wing = sh - sm
        skip       = upper_wing - lower_wing
        raw_credit = (upper_wing - lower_wing) * 0.15
        net_credit = round(max(raw_credit, 0.0), 2)

        mp   = round((lower_wing + net_credit) * 100, 2)
        ml   = round(max((lower_wing - net_credit) * 100, 0.0), 2)
        be_l = round(sm - mp / 100, 2)
        be_h = float(sh)
        exp  = get_nearest_expiry(ticker, dte)
        return StrategySignal(
            strategy_name="broken_wing_butterfly",
            strategy_display="Broken-Wing Butterfly 🦋⚡",
            category="BULLISH",
            ticker=ticker,
            underlying_price=price,
            leg1_strike=float(sl),
            leg2_strike=float(sm),
            leg3_strike=float(sh),
            net_credit=net_credit,
            net_debit=0.0,
            max_profit=mp,
            max_loss=ml,
            break_even_low=be_l,
            break_even_high=be_h,
            probability_of_profit=60.0,
            risk_reward_ratio=round(mp / ml, 2) if ml > 0 else 0,
            expiry_date=exp,
            dte=dte,
            iv_rank=iv_rank,
            is_broken_wing=True,
            skip_width=float(skip),
            close_at_profit_pct=0.50,
            manage_at_dte=21,
            close_target_dollar=round(mp * 0.50, 2),
        )

    # ── Telegram message formatter ────────────────────────────────────────────

    def format_telegram_message(self, signal: StrategySignal) -> str:
        """Return a Telegram-ready Markdown message for any StrategySignal."""
        s = signal
        n = s.strategy_name

        if n == "iron_condor":
            legs = (
                f"  מכור Put `${s.leg1_strike}` / קנה Put `${s.leg2_strike}`\n"
                f"  מכור Call `${s.leg3_strike}` / קנה Call `${s.leg4_strike}`\n"
                f"  קרדיט נטו: `${s.net_credit}`"
            )
        elif n == "bull_put_spread":
            legs = (
                f"  מכור Put `${s.leg1_strike}` / קנה Put `${s.leg2_strike}`\n"
                f"  קרדיט נטו: `${s.net_credit}` | Target delta: ~{s.target_delta}"
            )
        elif n == "bear_call_spread":
            legs = (
                f"  מכור Call `${s.leg1_strike}` / קנה Call `${s.leg2_strike}`\n"
                f"  קרדיט נטו: `${s.net_credit}` | Target delta: ~{s.target_delta}"
            )
        elif n == "cash_secured_put":
            legs = (
                f"  מכור Put `${s.leg1_strike}`\n"
                f"  פרמיה: `${s.net_credit}` | ביטחון: `${s.leg1_strike * 100:.0f}`\n"
                f"  תשואה על ההון: `{s.return_on_capital:.1f}%` (~`{s.annualized_return:.0f}%` שנתי)"
            )
        elif n == "covered_call":
            legs = (
                f"  מכור Call `${s.leg1_strike}` (בעלות על 100 מניות)\n"
                f"  פרמיה: `${s.net_credit}`\n"
                f"  תשואה על ההון: `{s.return_on_capital:.1f}%` (~`{s.annualized_return:.0f}%` שנתי)"
            )
        elif n == "bull_call_spread":
            legs = (
                f"  קנה Call `${s.leg1_strike}` / מכור Call `${s.leg2_strike}`\n"
                f"  דביט נטו: `${s.net_debit}`"
            )
        elif n == "bear_put_spread":
            legs = (
                f"  קנה Put `${s.leg1_strike}` / מכור Put `${s.leg2_strike}`\n"
                f"  דביט נטו: `${s.net_debit}`"
            )
        elif n == "long_straddle":
            legs = (
                f"  קנה Call + Put @ `${s.leg1_strike}` (ATM)\n"
                f"  דביט נטו: `${s.net_debit}` | תנועה נדרשת: `{s.move_needed_pct:.1f}%`"
            )
        elif n == "long_call_leap":
            legs = (
                f"  קנה Call `${s.leg1_strike}` (עמוק ITM, ~0.75Δ)\n"
                f"  דביט נטו: `${s.net_debit}` | תחליף מניה"
            )
        elif n == "short_strangle":
            legs = (
                f"  מכור Put `${s.leg1_strike}` / מכור Call `${s.leg2_strike}`\n"
                f"  קרדיט נטו: `${s.net_credit}` | ⚠️ סיכון בלתי מוגבל"
            )
        elif n == "calendar_spread":
            legs = (
                f"   מכור Call/Put ${s.leg1_strike} — פקיעה {s.near_expiry} ({s.near_dte} ימים)\n"
                f"   קנה  Call/Put ${s.leg2_strike} — פקיעה {s.far_expiry}  ({s.far_dte} ימים)\n"
                f"   אותו סטרייק ATM | דביט נטו: ${s.net_debit}"
            )
        elif n == "butterfly":
            legs = (
                f"   קנה  Call ${s.leg1_strike} (1x)\n"
                f"   מכור Call ${s.leg2_strike} (2x) ← מרוויח אם מניה נוחתת כאן\n"
                f"   קנה  Call ${s.leg3_strike} (1x)\n"
                f"   דביט נטו: ${s.net_debit}"
            )
        elif n == "call_back_ratio":
            credit_or_debit = (
                f"קרדיט נטו: ${s.net_credit}" if s.net_credit > 0
                else f"דביט נטו: ${s.net_debit}" if s.net_debit > 0
                else "עלות אפס (Zero Cost)"
            )
            legs = (
                f"   מכור {s.ratio_short}x Call ${s.leg1_strike} (ATM)\n"
                f"   קנה  {s.ratio_long}x Call ${s.leg2_strike} (OTM)\n"
                f"   {credit_or_debit}\n"
                f"   רווח בלתי מוגבל מעל ${s.leg2_strike}"
            )
        elif n == "broken_wing_butterfly":
            legs = (
                f"   קנה  Put ${s.leg1_strike} (1x) — כנף תחתונה\n"
                f"   מכור Put ${s.leg2_strike} (2x) — סטרייק קצר\n"
                f"   קנה  Put ${s.leg3_strike} (1x) — כנף עליונה שבורה ⚡\n"
                f"   קרדיט נטו: ${s.net_credit} | פוטנציאל שחיקה: ${s.skip_width:.0f}"
            )
        else:
            legs = "  ראה פרטים למעלה"

        max_loss_str   = f"${s.max_loss:.0f}"   if s.max_loss   < 9_999_990 else "בלתי מוגבל"
        max_profit_str = f"${s.max_profit:.0f}" if s.max_profit < 9_999_990 else "בלתי מוגבל"
        theta_str      = f"${s.theta_daily:+.2f}/day" if s.theta_daily else "—"
        vega_str       = f"${s.vega_per_1pct:+.2f}/1%" if s.vega_per_1pct else "—"
        cat_emoji      = "🟢" if s.category == "BULLISH" else ("🔴" if s.category == "BEARISH" else "⚪")

        # Capital efficiency block
        margin_block = ""
        if s.margin_required > 0:
            roc_str    = f"`{s.return_on_capital:.1f}%`" if s.return_on_capital else "—"
            eff_str    = s.capital_efficiency or "—"
            note_str   = f"\n  _{s.margin_note}_" if s.margin_note else ""
            margin_block = (
                f"\n💼 *הון נדרש לעסקה:*\n"
                f"  בטוחה: `${s.margin_required:.0f}` | תשואה על הון: {roc_str} {eff_str}{note_str}\n"
            )

        return (
            f"{cat_emoji} *{s.ticker}* — {s.strategy_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 מחיר: `${s.underlying_price:.2f}` | IV Rank: `{s.iv_rank:.0f}%`\n"
            f"\n*מבנה העסקה:*\n{legs}\n"
            f"\n*מטריקות:*\n"
            f"  רווח מקסימלי : `{max_profit_str}`\n"
            f"  הפסד מקסימלי : `{max_loss_str}`\n"
            f"  R/R           : `{s.risk_reward_ratio:.2f}`\n"
            f"  PoP           : ~`{s.probability_of_profit:.0f}%`\n"
            f"\n*Greeks (est.):*\n"
            f"  Theta: `{theta_str}` | Vega: `{vega_str}`\n"
            f"\nנקודות איזון: `${s.break_even_low:.2f}` — `${s.break_even_high:.2f}`\n"
            f"פקיעה: `{s.expiry_date}` (~`{s.dte}` DTE)\n"
            f"\n*ניהול העסקה:*\n"
            f"  סגור ב-50% רווח → `${s.close_target_dollar:.0f}`\n"
            f"  נהל / Roll ב-`{s.manage_at_dte}` DTE\n"
            + margin_block
            + (f"\n📰 *חדשות:* _{s.news_pulse}_\n" if s.news_pulse else "")
            + f"\n_{s.rationale}_"
        )
