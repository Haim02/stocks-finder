"""
backtest_engine.py — Options Strategy Backtester
=================================================
Based on: WealthCreating/Options-Backtesting-Prelim + renshoek/credit-spread-backtest
Tests Bull Put Spread historically using Black-Scholes pricing when real data unavailable.
Saves trade records to MongoDB collection 'training_events' for XGBoost feature enrichment.
"""

import math
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    ticker: str
    strategy: str
    start_date: str
    end_date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    total_pnl: float
    max_drawdown: float
    best_trade: float
    worst_trade: float
    sharpe_ratio: float


def _black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0:
        return max(K - S, 0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    from scipy.stats import norm
    N = norm.cdf
    return K * math.exp(-r * T) * N(-d2) - S * N(-d1)


def backtest_bull_put_spread(
    ticker: str,
    short_delta: float = 0.20,
    spread_width: float = 5.0,
    dte_target: int = 35,
    profit_target_pct: float = 0.50,
    stop_loss_mult: float = 2.0,
    lookback_days: int = 365,
) -> Optional[BacktestResult]:
    """
    Backtest Bull Put Spread historically.
    Entry every Monday when IV Rank >= 25 and RSI > 40.
    Exit at 50% profit or 2x loss (Tastytrade rules).
    """
    try:
        import yfinance as yf
        import pandas as pd
        import numpy as np

        stock = yf.Ticker(ticker)
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        hist = stock.history(start=start_date.isoformat(), end=end_date.isoformat())
        if hist.empty or len(hist) < 50:
            return None

        closes = hist["Close"]
        returns = closes.pct_change().dropna()
        rolling_vol = returns.rolling(20).std() * math.sqrt(252)

        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))

        trades = []
        i = 20

        while i < len(closes) - dte_target:
            price = float(closes.iloc[i])
            iv = float(rolling_vol.iloc[i]) if not pd.isna(rolling_vol.iloc[i]) else 0.25
            rsi_val = float(rsi.iloc[i]) if not pd.isna(rsi.iloc[i]) else 50.0

            window_vols = rolling_vol.iloc[max(0, i - 252):i]
            iv_min = float(window_vols.min()) if not window_vols.empty else iv * 0.5
            iv_max = float(window_vols.max()) if not window_vols.empty else iv * 1.5
            iv_rank = (iv - iv_min) / (iv_max - iv_min) * 100 if iv_max != iv_min else 50.0

            if iv_rank >= 25 and rsi_val >= 40:
                short_strike = round(price * (1 - iv * math.sqrt(dte_target / 365) * 0.8), 0)
                long_strike = short_strike - spread_width

                T = dte_target / 365
                r = 0.045
                short_price = _black_scholes_put(price, short_strike, T, r, iv)
                long_price = _black_scholes_put(price, long_strike, T, r, iv)
                credit = max(0.0, short_price - long_price)

                if credit < 0.30:
                    i += 5
                    continue

                future_prices = closes.iloc[i:i + dte_target]
                max_profit = credit * 100
                max_loss = (spread_width - credit) * 100
                min_future_price = float(future_prices.min())

                if min_future_price > short_strike:
                    pnl = max_profit * profit_target_pct
                    result = "WIN"
                elif min_future_price < long_strike:
                    pnl = -max_loss
                    result = "LOSS"
                else:
                    breach = (short_strike - min_future_price) / spread_width
                    pnl = -max_loss * breach
                    result = "PARTIAL_LOSS" if pnl < 0 else "WIN"

                trades.append({
                    "date": hist.index[i].strftime("%Y-%m-%d"),
                    "price": price,
                    "short_strike": short_strike,
                    "credit": credit,
                    "pnl": pnl,
                    "result": result,
                    "iv_rank": iv_rank,
                    "rsi": rsi_val,
                })

                i += dte_target
            else:
                i += 5

        if not trades:
            return None

        df = pd.DataFrame(trades)
        wins = df[df["pnl"] > 0]
        losses = df[df["pnl"] < 0]

        total_pnl = df["pnl"].sum()
        cumulative = df["pnl"].cumsum()
        drawdown = float((cumulative - cumulative.cummax()).min())

        returns_arr = df["pnl"].values
        sharpe = (returns_arr.mean() / (returns_arr.std() + 0.001)) * math.sqrt(12)

        bt_result = BacktestResult(
            ticker=ticker,
            strategy="Bull Put Spread",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_trades=len(df),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate=round(len(wins) / len(df) * 100, 1),
            avg_profit=round(float(wins["pnl"].mean()), 2) if not wins.empty else 0.0,
            avg_loss=round(float(losses["pnl"].mean()), 2) if not losses.empty else 0.0,
            total_pnl=round(float(total_pnl), 2),
            max_drawdown=round(drawdown, 2),
            best_trade=round(float(df["pnl"].max()), 2),
            worst_trade=round(float(df["pnl"].min()), 2),
            sharpe_ratio=round(float(sharpe), 2),
        )

        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            records = df.to_dict("records")
            for r in records:
                r["ticker"] = ticker
                r["strategy"] = "Bull Put Spread"
                r["source"] = "backtest"
            if records:
                db["training_events"].insert_many(records)
                logger.info("Saved %d backtest trades to MongoDB for XGBoost", len(records))
        except Exception as e:
            logger.warning("Could not save backtest trades to MongoDB: %s", e)

        return bt_result

    except Exception as e:
        logger.error("Backtest failed for %s: %s", ticker, e)
        return None


def format_backtest_hebrew(result: BacktestResult) -> str:
    """Format BacktestResult as Hebrew Telegram message."""
    win_emoji = "🟢" if result.win_rate >= 65 else ("🟡" if result.win_rate >= 50 else "🔴")
    pnl_emoji = "📈" if result.total_pnl > 0 else "📉"

    return (
        f"📊 *Backtest — {result.ticker} {result.strategy}*\n"
        f"📅 {result.start_date} → {result.end_date}\n"
        f"{'━' * 30}\n\n"
        f"📋 *עסקאות:* {result.total_trades}\n"
        f"{win_emoji} *Win Rate: {result.win_rate}%* "
        f"({result.winning_trades}W / {result.losing_trades}L)\n\n"
        f"💰 *רווח ממוצע: ${result.avg_profit}*\n"
        f"💸 *הפסד ממוצע: ${result.avg_loss}*\n"
        f"{pnl_emoji} *סה\"כ P&L: ${result.total_pnl:,.0f}*\n\n"
        f"📉 Max Drawdown: `${result.max_drawdown:,.0f}`\n"
        f"📊 Sharpe Ratio: `{result.sharpe_ratio}`\n"
        f"🏆 עסקה טובה: `${result.best_trade}`\n"
        f"💣 עסקה גרועה: `${result.worst_trade}`"
    )
