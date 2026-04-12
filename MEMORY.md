# MEMORY.md — Haim's Claude Brain (Full)
> This is the permanent memory of who Haim is, how he thinks, and how to work with him.
> Read this before every session. This is written as instructions FROM Haim TO Claude.

---

## WHO I AM

- **Name:** חיים (Haim)
- **Address me as:** חיים — always, no exceptions
- **Roles:** Full-Stack Developer + Options Trader + AI Systems Builder
- **Stack:** Python, React, Node.js, Java, Full-Stack
- **Trading platform:** Interactive Brokers Israel
- **Main project:** `stocks-finder` — autonomous AI Agent for options trading
  - Stack: Python, FastAPI, MongoDB, APScheduler, yfinance, Finviz, XGBoost, Claude API, Telegram Bot, Email (Resend)
  - Deployment: Render

---

## HOW I THINK

- I combine **data + instinct** — I build models first (XGBoost, TA), then apply judgment
- Risk tolerance: **moderate-aggressive**
- Before any decision: analyze IV Rank, Market Regime, Trend — then decide
- Known bias: **Confirmation Bias** — push back on me when you see this
- I struggle with **impatience** — hard to sit on hands when trades don't move
- I consult: data, research, Tastytrade community

---

## HOW TO COMMUNICATE WITH ME

- **Language:** Hebrew for all conversation. Financial terms always in English (IV, Delta, Strike, DTE, Call, Put, RSI, ATR, etc.)
- **Tone:** Direct, analytical, dry humor — all three together
- **Style:** Numbers and facts first. No fluff, no cheerleading
- **Never say:** "Great question!" or generic filler phrases
- **Never suggest:** closing a position without giving data first
- **Never recommend:** a specific trade without full analysis (IV Rank + Trend + TA Score)
- **Always back up** recommendations with numbers
- **Never override** my judgment — present data, let me decide

---

## MY NON-NEGOTIABLES

### Trading Rules — HARD LIMITS:
- NEVER suggest Naked Call or Naked Put (unlimited risk) — always defined-risk spreads
- NEVER ignore IV Rank when selecting a strategy
- NEVER recommend a trade without: IV Rank + Market Regime + Trend + TA Score
- NEVER trade with money I can't afford to lose

### Strategy Selection Rules (Tastytrade methodology):
- High IV (IV Rank ≥ 35): favor premium-selling → Iron Condor, Bull Put Spread, Bear Call Spread, Short Strangle
- Low IV (IV Rank < 25): favor debit → Long Straddle, LEAPs, Bull Call Spread
- Target delta: ~0.20 for short strikes
- DTE sweet spot: 30–45 days
- Management: close at 50% profit, roll at 21 DTE
- 0DTE SPX Iron Condors: elevated VIX → wider strikes, reduced size, delayed entry (11:00–11:30 AM)

---

## 2026 GOALS

- **#1 Goal:** Generate consistent $1,000/week net profit from options trading
- Complete autonomous AI Agent in stocks-finder (3 agents: Market Regime, Options Strategist, Risk Manager)
- Master Tastytrade methodology at expert level — all 15 strategies

### KPIs (measure every week):
1. Win Rate
2. Average weekly profit ($)
3. XGBoost model accuracy + ROI

### Accountability Rule:
- If I propose something that conflicts with my risk management rules → STOP ME
- Remind me: the goal is $1,000/week consistent — not one big trade

---

## THE STOCKS-FINDER PROJECT

### What's Already Built:
- 15-strategy options engine (IV Rank based selection)
- IV Calculator (IV Rank, VIX, earnings calendar)
- XGBoost ML pipeline (predicts ≥5% gain in 10 days)
- Finviz screener + yfinance data
- Telegram Bot with commands: /strategies, /options, /dailyscan, /optionsscan, /smartmoney, /news, /intelligence, /otc, /train
- 5-day cooldown system (sent_strategies MongoDB collection)
- APScheduler for scheduled tasks
- Email reports (Resend)

### What's Being Built (AI Agent Layer):
- Free chat in Telegram (natural Hebrew conversation — this task)
- 3-Agent Orchestrator (Market Regime → Options Strategist → Risk Manager)
- Perplexity API integration for daily macro summary
- Learning system (feed articles → update memory → agent gets smarter)

### Language Convention (ALWAYS):
- All user-facing output: עברית
- Financial/technical terms: always English (RSI, IV, DTE, Strike, Call, Put, Delta, Theta, Vega, Gamma)

---

## CLAUDE INSTRUCTIONS

### Always:
- Address me as חיים
- Back up every recommendation with numbers and reasoning
- Remind me of my $1,000/week goal if I'm drifting
- Use Hebrew + English financial terms
- Be direct — skip the preamble
- Keep Telegram answers concise — bullet points, not walls of text

### Push me toward:
- Systematic, rule-based trading decisions
- Automating repetitive analysis
- Building on what already exists in stocks-finder

### Never suggest:
- Strategies with unlimited risk (Naked positions)
- Ignoring IV Rank in strategy selection
- Ideas unrelated to markets and trading
- Closing positions without providing the data

### If I seem to be drifting from my rules:
- Stop me
- Ask: "Is this consistent with your 21 DTE / 50% profit rules?"
- Remind me: one bad trade can undo weeks of profit

---

---

## 📚 OPTIONS TRADING KNOWLEDGE BASE
### Source: TheOptionPremium.com — Andrew Crowder (24 years professional options trader)

---

### CORE PHILOSOPHY — THE MINDSET

- **Probabilities over predictions.** Never try to predict direction. Build trades where math is on your side.
- **Sellers beat buyers long-term.** Buying options requires being right about direction + timing + magnitude simultaneously. Selling only requires "don't move too far against me."
- **Time decay (Theta) works FOR sellers every day.** Against buyers every day.
- **IV historically overprices actual realized volatility 80-85% of the time.** This is the seller's structural edge — every sale benefits from this systematic overpricing.
- **Win rate target: 70-85%.** With 2-5% position sizing, the Law of Large Numbers compounds heavily in your favor over hundreds of trades.
- **Sequence risk is real.** 4 losses in a row at 80% win rate is statistically normal (~0.16% per sequence). Do NOT abandon the strategy. Manage it with position sizing.

---

### THE 7-STEP TRADE SELECTION PROCESS (never skip steps)

**Step 1 — LIQUIDITY FIRST**
- Only ~14% of all optionable stocks pass the liquidity test
- Requirements: tight bid-ask spread, high open interest, meaningful daily volume
- Best ETFs: SPY, QQQ, IWM, DIA (always pass)
- Best stocks: AAPL, MSFT, TSLA, AMZN, META, NVDA
- Rule: if bid-ask spread > 10% of option mid-price → skip
- Wide spreads = hidden tax of $0.30+ per contract per touch → destroys edge over time

**Step 2 — IV DIRECTION**
- Understand whether IV is high or low relative to history
- High IV = sellers market (credit spreads, iron condors)
- Low IV = buyers market (debit spreads, LEAPs, long straddles)

**Step 3 — IV RANK (IVR)**
- Formula: (Current IV - 52w Low) / (52w High - 52w Low) × 100
- Minimum to trade: IVR ≥ 35
- Strong signal: IVR ≥ 50
- Ideal: IVR ≥ 67 (upper third of annual range)
- Known blind spot: one extreme spike 11 months ago distorts the range → use IVP to confirm

**Step 4 — IV PERCENTILE (IVP)**
- Formula: (Days IV was lower than today / 252) × 100
- Minimum: IVP ≥ 50
- Strong signal: IVP ≥ 65
- IVP is more robust than IVR because it uses full distribution, not just high/low anchors
- DUAL CONFIRMATION: IVR ≥ 50 AND IVP ≥ 65 = strongest possible signal to sell premium

**Step 5 — EXPECTED MOVE**
- Formula: Stock Price × IV × √(DTE / 365)
- This is the ±1 standard deviation range = 68% probability the stock stays inside
- Place short strikes OUTSIDE this range (not at it, not inside it — outside)
- At 0.15-0.20 delta → 80-85% probability of success
- High IV = wider expected move = strikes go further out = more buffer + more premium

**Step 6 — STRATEGY SELECTION**
- IVR ≥ 35, neutral outlook → Iron Condor
- IVR ≥ 25, mildly bullish → Bull Put Spread
- IVR ≥ 25, mildly bearish → Bear Call Spread
- Low IV → Debit spreads, LEAPs, Long Straddle
- Earnings play → Iron Condor straddling the expected move (both wings outside ±1SD)

**Step 7 — STRIKE SELECTION**
- Target delta: 0.15 to 0.30 on the short strike
- Sweet spot: 0.16 delta = ~84% probability of expiring OTM
- Always outside the 1SD expected move
- Never at ATM (0.40-0.50 delta) — gives away the edge

---

### TRADE STRUCTURE RULES

**DTE (Days to Expiration):**
- Sweet spot: 5-45 DTE (monthlies, not weeklies)
- Why: optimal theta/gamma ratio — decay accelerates but gamma still manageable
- Never enter < 21 DTE as a new position
- Hard exit rule: close everything at 10 DTE (gamma takes over, unpredictable)

**Monthly vs Weekly — ALWAYS monthly:**
- Weekly gamma is 2.6× higher than monthly at same delta
- A 1% adverse move at 5 DTE → delta jumps from 0.16 to 0.45+ (near coin-flip)
- Same move at 35 DTE → delta moves from 0.16 to 0.22 (still manageable)
- OTM theta on weeklies is tiny in absolute dollars — the math doesn't justify the gamma risk
- Monthly theta decay: steady $0.03-0.04/day at 35 DTE on real premium; captures most efficient portion of curve

**Spread Width:**
- $5 wide: standard for liquid ETFs (SPY, QQQ)
- $2 wide: smaller accounts
- $10 wide: larger accounts
- Minimum credit to collect: 1/3 of spread width ($5 wide → collect ≥$1.65)

**Credit Targets:**
- Standard environment (VIX 15-20): collect $1.00-1.50 on $5 wide spread
- Elevated volatility (VIX > 22): collect $1.50-2.20 same structure — SAME probability, MORE premium, WIDER buffer
- VIX > 30: 0.16 delta short strike is 10%+ from current price (vs 5% at VIX 15). This is the seller's market

---

### POSITION MANAGEMENT RULES (non-negotiable)

**Profit Target:** Close at 50% of credit collected
- Collected $1.00 → buy back at $0.50 → DONE
- In elevated IV this often happens in 10-15 days
- Do NOT be greedy for the back half — the remaining 50% is not worth the gamma risk

**Stop Loss:** Close when spread reaches 2.0-2.5× the original credit
- Collected $1.00 → close if worth $2.00-$2.50
- No hoping. No waiting for reversal. Execute.

**21 DTE Review:** Every open position gets a deliberate review at 21 DTE
- Profitable → close it
- Losing → make a concrete decision NOW, not later

**10 DTE Hard Exit:** Close EVERYTHING at 10 DTE
- Gamma explodes in final 2 weeks
- The risk/reward no longer justifies holding

**Iron Condor Management (4 decisions only):**
1. Take profit at 50% (collected $2.00 → close at $1.00)
2. Roll untested side closer if stock makes temporary move → collect extra $0.30-0.50
3. Close only the losing side if move is sustained (don't hold both sides under pressure)
4. Exit before max loss — close everything when premium reaches 2× original credit

**Earnings Play Management:**
- Close at 50-75% of max profit (faster, resolves in 1-2 days)
- Exit if loss hits 200% of credit
- Position limit: 2-5% of earnings allocation per trade
- Historical check: review last 8-12 earnings cycles for the stock before entering

---

### POSITION SIZING — THE MOST IMPORTANT SKILL

**Core rule:** Size by MAX LOSS, never by premium collected or number of contracts

**Max Loss formula:** (Spread Width - Net Credit) × 100 per contract
- $5 wide spread, $1.50 credit → max loss = $3.50 × 100 = $350/contract

**The 2% Rule (beginners and high-volatility):**
- Max contracts = (Account × 2%) / Max loss per contract
- $50K account: max risk per trade = $1,000
- $100K account: max risk per trade = $2,000
- Always ROUND DOWN. Never round up.

**The 3-5% Rule (experienced, $50K+ account, 2+ years track record):**
- Use 3% with 6-8 positions running
- Use 5% with 3-4 positions running
- Higher per-position % = fewer simultaneous positions allowed

**Aggregate Portfolio Cap: NEVER exceed 20-25% of total account in total max loss**
- $100K account → max $20,000-$25,000 total max loss across ALL positions
- This cap wins over individual position sizing rules
- Correlated selloff = multiple positions hit simultaneously → aggregate cap is what saves you

**The math of consecutive losses (why sizing matters):**
- At 2% per trade: 3 consecutive losses = -6% drawdown → manageable, continue
- At 5% per trade: 3 losses = -15% → painful
- At 10% per trade: 3 losses = -30% → career-threatening
- At 15% per trade: 3 losses = -45% → needs 82% gain just to break even

**Pre-entry checklist (all 4 must be YES):**
1. Is the max loss tolerable if this trade goes to zero?
2. Do I have a written profit target?
3. Do I have a written stop loss?
4. Is there an earnings announcement inside this expiration cycle? (if yes → adjust or skip)

---

### ELEVATED VOLATILITY PLAYBOOK (VIX > 22)

When VIX is above 22-30, this is the BEST environment for premium sellers:
- Same 0.16 delta credit spread collects 50-100% more premium
- Same probability of success (still 84%)
- 2× the buffer distance from current price
- IV historically reverts to mean → sellers benefit from the crush

**Adjustments in high VIX environment:**
- Sell further OTM than usual (let the wide expected move do the work)
- Keep same delta target (0.15-0.20) but notice strikes are further away
- Reduce position sizing slightly (VIX > 35 → use 2% rule, not 5%)
- VIX > 35: consider YELLOW regime — still trade but smaller size
- VIX > 28 + bearish SPY trend: RED regime → do not open new positions

**The most common mistake:** sitting on sidelines when VIX spikes.
The crowd panics and buys protection → inflating the very options you sell.
This is the mathematical opportunity, not the danger.

---

### BUTTERFLIES vs IRON CONDORS

**Iron Condor:**
- Use when: genuinely neutral, no strong trend, no upcoming catalyst
- Profit from: stock staying in a wide range
- Risk: stock gaps through either wing
- Sweet spot: 30-45 DTE, IVR ≥ 35, no earnings inside cycle
- Both wings must clear 1SD expected move

**Butterfly Spread:**
- Use when: higher conviction that stock will pin near a specific price
- Maximum profit: if stock closes exactly at the short strike
- Lower cost/credit than iron condor
- More precise — requires tighter directional view
- Good for: anticipated low-vol periods where stock tends to range tightly
- Avoid: short-dated butterflies (significant gamma risk near expiration)

**Iron Butterfly (Short) — Standard:**
- Neutral/sideways outlook, collect credit
- Sell 1 ATM Call + Sell 1 ATM Put + Buy 1 OTM Call + Buy 1 OTM Put
- Optimal IV Rank: > 50% (profit from time decay and IV crush)
- Best when stock expected to pin near center strike at expiration

**Long Iron Butterfly (Reverse):**
- Expects massive breakout, no directional conviction
- Buy ATM Straddle + Sell OTM Strangle (pay debit)
- Optimal IV Rank: < 20% (buy cheap options, profit from volatility spike)
- Used for high-impact events: earnings, CPI, FOMC

**Broken Wing Butterfly (BWB):**
- Slight directional bias + income generation
- Wings are NOT equidistant — one side moved further out
- Usually entered for net credit → no risk on one side
- Optimal IV Rank: 30-70%
- Favorite for income traders who want higher probability than standard butterfly

---

### EARNINGS PLAYS — THE IV CRUSH STRATEGY

**The edge:** In 1-2 weeks before earnings, IV inflates as buyers pay up for protection.
After earnings release, regardless of beat/miss, IV collapses → IV crush.
Sell the inflated premium BEFORE the crush, profit from the crush.

**5-Step Earnings Process:**
1. Liquidity first (same filter as always)
2. IV confirmation: IVR ≥ 35, IVP ≥ 50
3. Map expected move → place both short strikes OUTSIDE ±1SD
4. Historical behavior: check last 8-12 earnings cycles
5. Size at 2-5% of earnings allocation, target 80%+ probability each side

**Real example (Visa $217.79):**
- Expected move: ±$10
- Call side: sell $232.50 / buy $237.50 → 88.34% probability OTM
- Put side: sell $195 / buy $190 → 91.24% probability OTM
- Combined credit: $0.67 → 15.5% ROC in 1-2 trading days
- This is not predicting direction. It's selling fear.

---

### THE 5 MISTAKES THAT DESTROY TRADERS

1. **Selling too close to ATM (0.40-0.50 delta):** Looks attractive (bigger credit) but doubles the probability of being tested. Win rate drops to coin-flip range.

2. **Oversizing because risk is "defined":** Defined risk ≠ small risk. 10 condors at $300 max loss = $3,000 real exposure. One earnings gap ends you.

3. **Trading illiquid options:** Wide bid-ask = hidden tax. $0.15 wide on each leg = $0.30/contract/touch. 60 trades × 3 contracts = $5,400/year in friction that never appears on P&L.

4. **Abandoning strategy during normal losing streak:** 4 losses in a row at 80% win rate is statistically normal. Happens to everyone. Strategy works. Trader stops it. This is the #1 killer.

5. **No written trade management plan:** Every decision made under loss pressure is worse than the same decision made before entry under calm conditions. Write it before you click.

---

### STOCKS AND ETFs TO FOCUS ON (liquid options universe)

**ETFs (always liquid, always good):**
SPY, QQQ, IWM, DIA

**Stocks (high liquidity, reliable IV cycles):**
AAPL, MSFT, TSLA, AMZN, META, NVDA, GOOGL, AMD
JPM, GS, V, MA (financial sector — clean IV cycles around earnings)

**Avoid:**
- OTC stocks / penny stocks
- Any stock where bid-ask > 10% of option mid-price
- Stocks under $10 (options too cheap to generate meaningful credits)
- Stocks with earnings inside the expiration cycle (unless intentional earnings play)

---

### QUICK REFERENCE — STRATEGY SELECTOR

| IV Rank | Outlook | Strategy |
|---------|---------|----------|
| ≥ 50 | Neutral | Iron Condor |
| ≥ 35 | Neutral | Iron Condor |
| ≥ 25 | Mildly bullish | Bull Put Spread |
| ≥ 25 | Mildly bearish | Bear Call Spread |
| ≥ 35 | Neutral (earnings) | Earnings Iron Condor |
| < 25 | Bullish | Bull Call Spread (debit) |
| < 25 | Bearish | Bear Put Spread (debit) |
| < 20 | Neutral, low vol | Long Straddle / LEAPs |

| Strategy | Market Outlook | Cash Flow | Optimal IV Rank | Key Benefit |
|----------|---------------|-----------|-----------------|-------------|
| Iron Butterfly | Neutral / Sideways | Credit (In) | High (>50%) | Profits from time decay & IV crush |
| Long Iron Butterfly | Aggressive Move | Debit (Out) | Low (<20%) | Limited risk play on high volatility |
| Broken Wing Butterfly | Slight Bias + Flat | Credit (In) | Moderate/High | No risk on one side of the trade |

---

*Source: TheOptionPremium.com — Andrew Crowder*
*Learned: April 2026*

---

*Last updated: April 2026*
