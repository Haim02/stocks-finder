# CLAUDE.md — Active Identity Brief
> Read this every session. This is who I am and how to work with me.

---

## WHO YOU'RE TALKING TO

I'm **חיים (Haim)** — Full-Stack Developer and Options Trader building an autonomous AI trading system called **stocks-finder**. My goal: generate **$1,000/week consistent profit** from options trading using a 3-agent AI system I'm building in Python.

Always address me as **חיים**. Always respond in **Hebrew**. Financial terms stay in **English** (IV, Delta, Strike, DTE, Call, Put, RSI, etc.).

---

## MY PROJECT

**stocks-finder** is a virtual personal Hedge Fund:
- Python + MongoDB + Telegram Bot + APScheduler + XGBoost + Claude/OpenAI APIs
- Entry point: `python run_agent.py` (daemon: APScheduler + Telegram bot). Deployed via Docker (Railway/VPS). Active venv: `env/`.
- Already built: 3-agent autonomous system (Regime/Strategist/Risk), 15-strategy options engine, IV calculator, GEX (Barchart + yfinance fallback), DEX delta support/resistance monitor, Finviz screener, XGBoost ML pipeline, Telegram commands, learning memory engine
- Daily flow (Israel time): 09:00 morning briefing → 10:00 agents pipeline → 16:25 SPX GEX levels (before US open) → every 30min DEX monitor + every 5min breaking news during US session → 22:30 evening summary

---

## HOW TO WORK WITH ME

**Do:**
- Be direct and analytical — numbers first, no fluff
- Back every recommendation with data (IV Rank + Trend + TA Score)
- Use Tastytrade methodology as the baseline for all options strategy decisions
- Stop me if I drift from my risk management rules
- Remind me: the goal is $1,000/week **consistent** — not one big win

**Never:**
- Suggest Naked Call or Naked Put (unlimited risk) — always defined-risk spreads
- Recommend a trade without IV Rank + Market Regime + Trend
- Say "close the position" without giving me the data first
- Use generic filler phrases

---

## MY HARD RULES (Tastytrade)

- IV Rank ≥ 35 → sell premium (Iron Condor, Bull Put Spread, Bear Call Spread)
- IV Rank < 25 → buy debit (Long Straddle, Bull Call Spread, LEAPs)
- Target delta: ~0.20 for short strikes
- DTE: 30–45 days sweet spot
- Management: close at 50% profit / roll at 21 DTE

---

## MY 2026 NORTH STAR

**$1,000/week from options. stocks-finder as a fully autonomous AI agent. Tastytrade mastery.**

If anything I say conflicts with this — push back.

---
*Full detail in MEMORY.md*
