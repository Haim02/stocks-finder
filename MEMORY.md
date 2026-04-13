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

## 📊 DATA SOURCES & CAPABILITIES (Updated April 2026)

### Macro Data — FRED (Federal Reserve Economic Data)
- **fredapi** connected to real FRED database
- Data: Fed Funds Rate, CPI, PCE, 10Y Treasury, Yield Curve, Unemployment, Recession Probability
- Update frequency: daily (Fed Funds) to monthly (CPI, PCE)
- Key insight: Inverted yield curve (10Y-2Y < -0.5%) = recession signal → Agent 1 turns RED
- Key insight: Recession probability > 50% → Agent 1 turns RED
- Free API key from: fred.stlouisfed.org

### Options + Equity Data — OpenBB (when installed)
- Open source terminal: github.com/OpenBB-finance/OpenBB
- Enhances IV Rank calculation beyond yfinance approximation
- Earnings calendar integration
- Macro indicators as secondary source
- Large install (~500MB) — optional, system falls back gracefully if absent

### Data Priority Stack:
1. FRED → macro regime (most accurate for Fed/CPI/rates)
2. OpenBB → IV Rank enhancement (when available)
3. yfinance → options chains, real-time prices, IV calculation
4. Perplexity → real-time news and events
5. OpenAI GPT-4o-mini → batch sentiment scoring
6. Claude Sonnet → analysis, commentary, free chat

### What the Agent Knows About Macro Regimes:
- **Expansion**: Fed rate moderate, CPI near target, yield curve positive → GREEN
- **Slowdown**: Yield curve flat/slightly inverted, S&P weak → YELLOW
- **Stagflation**: High CPI + high unemployment → YELLOW/RED
- **Recession**: Inverted yield curve (< -0.5%) + recession prob > 50% → RED
- **Recovery**: Strong S&P, falling unemployment, CPI declining → GREEN

---

## 📚 COMPREHENSIVE OPTIONS STRATEGY KNOWLEDGE BASE
### Source: Multiple courses + practical trading guides (April 2026)

---

### CORE PRINCIPLE — THE OPTIONS SELLER MINDSET

Every trade has a defined structure. Plan ALL outcomes before entering:
1. Stock stays above Strike → keep premium ✅
2. Stock drops but I still like it → Roll Down & Out, collect more premium
3. I get assigned → buy shares I wanted at a discount → start Covered Call cycle

**"No outcome is a surprise."** — JasonL_Capital

IV historically overprices actual volatility 80-85% of the time.
This is the structural edge for sellers. Never forget it.

---

### STRATEGY 1: CASH-SECURED PUT (CSP)

**Market:** Bullish to Neutral-Bullish
**Core idea:** Get paid to agree to buy shares at a price you WANT to own them at.

**Setup rules:**
- Only sell CSPs on stocks you'd HAPPILY OWN for years if assigned
- Strike (Short Put): Delta 0.20-0.25 (~80% probability of keeping premium)
- DTE: 30-45 days (monthly expiration closest to ~35 DTE)
- IV Rank minimum: 35 (premium must justify the risk)
- Collateral: Strike × 100 held in cash
- Credit target: minimum 1% of collateral per month

**Real example (from course):**
- $IREN: Sell $35 Put expiring 4/17
- Collateral: $3,500 | Premium: $163
- Return: 4.7% in 36 days = 47% annualized
- IV: 103.44% | Delta: -0.1998 | Theta: -0.0573

**Management:**
- Close at 50% profit (collected $1.50 → buy back at $0.75)
- Roll Down & Out if approaching strike: close current, sell lower strike further out
- If assigned → DO NOT PANIC → move to Covered Call phase

**Do NOT use CSP on:**
- Stocks you don't want to own
- Stocks with earnings inside the expiration cycle (unless intentional)
- Illiquid options (bid-ask spread > 10% of mid-price)

---

### STRATEGY 2: COVERED CALL (CC)

**Market:** Neutral to Mildly Bullish (when already owning 100 shares)
**Core idea:** Collect premium on shares you already hold. If called away — sell at profit.

**Setup rules:**
- Own 100 shares of the underlying
- Sell Call OTM: Delta 0.20-0.30
- Strike: above current price + above your cost basis
- DTE: 30-45 days
- IV Rank: ≥ 30

**Real example (from course):**
- $HOOD: Sell $90 Covered Call expiring 4/17
- Premium: $1.40 | IV: 56.86% | Delta: 0.2088 | Theta: -0.0610

**Management:**
- Close at 50% profit
- Roll Out (same strike, later expiration) if approaching strike with profit still available
- If called away → profit realized on shares + premium collected → return to CSP phase

---

### STRATEGY 3: THE WHEEL STRATEGY

**Market:** Long-term bullish. Works in ANY environment if stock is chosen correctly.
**Core idea:** Continuous income generation through a repeating CSP → CC cycle.

**The complete cycle:**
```
PHASE 1: Sell Cash-Secured Put
  → Stock stays above strike: Keep premium → repeat Phase 1
  → Stock drops below strike: Get Assigned → go to Phase 2

PHASE 2: Own 100 shares at discounted cost basis
  (Cost basis = Strike - Premium collected)
  → This is NOT a loss. It's the system working.

PHASE 3: Sell Covered Calls against shares
  → Stock stays below call strike: Keep premium → repeat Phase 3
  → Stock rises above call strike: Shares called away → go to Phase 4

PHASE 4: Shares sold at profit + Capital gains
  → Every phase generated income. Capital is free. Go back to Phase 1.
```

**Critical rule:** Every phase generates income. There is NO market environment where the Wheel leaves you doing nothing.

**Best underlying for Wheel:** SPY, QQQ, AAPL, MSFT, AMZN — liquid, stable, you'd want to own them.

**Avoid for Wheel:** Volatile meme stocks, pre-earnings setups, stocks below $30.

---

### STRATEGY 4: BULL PUT SPREAD

**Market:** Bullish to Neutral
**Core idea:** Sell Put at higher strike, buy Put at lower strike. Defined risk version of CSP.

**Structure:**
- Sell Put at Strike A (OTM, Delta ~0.20)
- Buy Put at Strike B (further OTM, Delta ~0.10)
- Width: $5 (standard for liquid ETFs)
- Net credit = premium sold - premium bought
- Max profit: net credit
- Max loss: (Width - Credit) × 100

**Example with $5 wide spread:**
- Stock at $100 | Sell $95 Put for $2.00 | Buy $90 Put for $0.50
- Net credit: $1.50 ($150 per spread)
- Max loss: $350 per spread
- Breakeven: $93.50 (6.5% cushion)

**Setup rules:**
- Short Strike Delta: 0.20-0.25 (outside 1SD expected move)
- Collect minimum: 1/3 of spread width ($5 wide → collect ≥ $1.65)
- DTE: 30-45 days
- IV Rank: ≥ 25 (minimum), ≥ 35 (preferred)

**Management:**
- Close at 50% profit
- Stop loss: 2-2.5× credit collected
- Review at 21 DTE
- Hard exit at 10 DTE (gamma risk)

---

### STRATEGY 5: BEAR CALL SPREAD

**Market:** Bearish to Neutral
**Core idea:** Sell Call at lower strike, buy Call at higher strike. Mirror of Bull Put Spread.

**Structure:**
- Sell Call at Strike A (OTM above price, Delta ~0.20)
- Buy Call at Strike B (further OTM, Delta ~0.10)
- Profit when stock stays BELOW short strike

**When to use:**
- Stock in clear downtrend
- Near resistance level
- After rejection from major moving average
- High IV environment (IV Rank ≥ 25)

**Never use Bear Call Spread in a strong bullish trend.**

**Same management rules as Bull Put Spread.**

---

### STRATEGY 6: IRON CONDOR

**Market:** Neutral — stock expected to stay in a defined range
**Core idea:** Bull Put Spread (below) + Bear Call Spread (above) = collect from both sides.

**Structure:**
- Sell Put at Strike A (below current price, Delta ~0.16-0.20)
- Buy Put at Strike B (further below, protection)
- Sell Call at Strike C (above current price, Delta ~0.16-0.20)
- Buy Call at Strike D (further above, protection)
- Profit zone: stock stays between Strike A and Strike C

**Example:**
- Stock at $200
- Buy $185 Put / Sell $190 Put / Sell $210 Call / Buy $215 Call
- Total credit: $2.00 | Profit zone: $190-$210 | Breakevens: $188 and $212

**Requirements:**
1. Genuinely neutral outlook — no strong trend
2. IV Rank ≥ 35 (MANDATORY — need rich premium on both wings)
3. NO earnings inside expiration window
4. Both short strikes outside 1SD expected move

**Management (4 decisions only):**
1. Take profit at 50% of credit
2. Roll untested side closer if stock makes temporary move (collect extra $0.30-0.50)
3. Close only the losing side if move is sustained
4. Exit before max loss — close everything if premium reaches 2× credit

**Do NOT hold to expiration.** Hard exit at 10 DTE.

---

### STRATEGY 7: POOR MAN'S COVERED CALL (PMCC)

**Market:** Bullish long-term
**Core idea:** Replace 100 shares with a deep ITM LEAP call. Run Covered Call strategy at 65% less capital.

**Structure:**
- Step 1: Buy deep ITM LEAP Call (Delta 0.80+, 1+ year out) → the "shares"
- Step 2: Sell short-term OTM Call (~30 DTE, Delta ~0.20) against it → income
- Step 3: Collect premium monthly, repeat

**Capital comparison:**
- Traditional Covered Call on $100 stock: $10,000
- PMCC on same stock: ~$3,500 (just the LEAP)
- **65% less capital for similar exposure**

**Key insight:** The REAL profit comes from the LEAP appreciating as the stock rises. The monthly premiums are a BONUS that reduces your cost basis each month.

**Risks:**
- LEAP loses value if stock drops (leveraged downside)
- Theta decay affects the LEAP over time (less than short options)
- Never sell the short call above the LEAP strike (creates spread, not PMCC)

**DO NOT USE PMCC until you've mastered CSP and CC.**

---

### STRATEGY 8: CALENDAR SPREAD

**Market:** Neutral, expecting IV to rise
**Core idea:** Sell short-term option, buy longer-term option at same strike. Profit from time decay difference and IV expansion.

**Best environment:** Low IV (cheap to buy the long option)
**Profit from:** Theta decay of short leg + IV increase on long leg

**Avoid:** High IV environments (long option becomes expensive relative to premium collected)

---

### STRATEGY 9: LONG CALL / LEAPs

**Market:** Strongly bullish
**Core idea:** Leveraged bullish bet with defined risk.

**When to buy LEAPs:**
- IV is LOW (cheap premium)
- You have high conviction on direction
- You want leverage without unlimited downside

**Setup:**
- Delta: 0.70-0.80+ (Deep ITM — moves almost like owning shares)
- DTE: 1+ year (enough time for thesis to play out)
- Avoid buying ATM or OTM long calls (Theta kills you)

**"Don't confuse a cheap premium with a good deal. Far OTM options look like bargains but have dramatically lower chance of working."**

---

### STRATEGY 10: SHORT STRANGLE (Advanced — VIX Spikes)

**Market:** Neutral, VERY high IV environment (VIX spikes, IVR ≥ 50)
**Core idea:** Sell OTM Put AND OTM Call simultaneously. Collect premium from both sides.

**From course (Image 7):**
- Use when VIX spikes — shift to selling naked puts and strangles
- Effectively selling volatility
- IVR must be ≥ 50
- Prefer SPY or QQQ (less volatile, better liquidity)

**WARNING:** Undefined risk on both sides. Requires:
- Large Margin account
- Portfolio Margin approval at IB
- Very active position management
- NEVER use on single volatile stocks

**This strategy is NOT suitable for small accounts.**

---

### STRATEGY 11: 0DTE CREDIT SPREADS (Ultra-Advanced)

**Market:** Any — but requires full-time monitoring
**Core idea:** Sell same-day expiration credit spreads. Rapid Theta decay.

**Method (from Image 10):**
- Buy Vega wings 1-7 DTE (protection)
- Sell 0DTE credit spreads with Delta 7-20 (7-20% probability of being tested)
- Entry: 2 minutes after market open
- Exit: 10 minutes before close
- 150-200 trades per day → ~100% annual return possible

**Requirements:**
- Full-time monitoring (cannot leave positions unattended)
- Very fast execution platform
- Deep understanding of Gamma Risk
- Large enough account to absorb daily fluctuations

**THIS IS NOT SUITABLE FOR PART-TIME TRADERS.**

---

### STRIKE SELECTION GUIDE (from courses)

**ITM (In The Money) — Delta 0.50-0.90:**
- Most conservative for selling
- Moves closely with stock
- Less leverage, highest probability of profit
- Higher capital required

**ATM (At The Money) — Delta ~0.50:**
- Middle ground
- Balance of cost, leverage, and probability
- Used for straddles/strangles

**OTM (Out of The Money) — Delta 0.10-0.30:**
- For credit spreads: Delta 0.15-0.25 (sweet spot)
- For buying: need strong directional conviction
- Far OTM (~0.05 Delta): lottery ticket — avoid as primary strategy

**"Don't confuse a cheap premium with a good deal."**

---

### IV DECISION MATRIX (from courses)

| IV Environment | Action |
|---------------|--------|
| High IV (IVR ≥ 50) | Sell premium aggressively |
| High IV + oversold | Sell Cash-Secured Puts |
| High IV + overbought | Sell Covered Calls |
| High IV + neutral | Iron Condor / Short Strangle |
| Low IV (IVR < 25) | Buy options (LEAPs, Long Calls) |
| Low IV + oversold | Buy long-dated calls |
| Low IV + neutral | Calendar Spread |

---

### PRACTICAL TRADING RULES (from multiple courses)

**7 Non-Negotiable Rules:**
1. Only sell options on stocks I'd happily own for years (CSP/Wheel)
2. Target ~0.20 delta (~80% probability of keeping premium)
3. 30-45 DTE sweet spot (monthlies, never weeklies for swing trading)
4. Close at 50% profit — always, no exceptions
5. Check IV environment first — HIGH IV = sell, LOW IV = buy LEAPs
6. Liquidity is non-negotiable — tight bid-ask spreads or move on
7. Always have a written exit plan BEFORE entering any trade

**9 Practical Tips (RanOptions course):**
1. ATM options are "explosive" — take profits fast when near expiration
2. In volatile stocks, options are expensive — trade patiently
3. When OTM becomes deep ITM — trade it like stock ownership
4. When IV is very high — expect IV crush, use selling strategies
5. If you bought an option and IV rose sharply — good time to sell
6. Don't hedge during a crisis — build protection BEFORE the market prices in the drop
7. "Solid" options = deep ITM, behaves like 100 shares
8. Take profits fast — especially when approaching expiration
9. Invest only what you can afford to lose to zero (options decay)

---

### EARLY ASSIGNMENT & PIN RISK (from RanOptions course)

**Pin Risk (buying options):**
- If option expires slightly ITM → broker automatically exercises it
- You wake up Monday with 100 shares (Call) or -100 shares (Put)
- Weekend gap risk can be catastrophic
- Solution: **Always close options before expiration if near the strike**

**Pin Risk (selling options):**
- Buyer can exercise up to 1 HOUR after market close on expiration day
- Even if expired OTM, after-hours news can push it ITM
- Then you get assigned Monday morning at a bad price
- Solution: **Close all short options before end of expiration day**

---

### BLACK-SCHOLES & IV UNDERSTANDING (from RanOptions course)

**Black-Scholes inputs:**
- Stock price | Strike price | Time to expiration | Implied Volatility | Risk-free rate

**IV = Implied Volatility:**
- Derived BACKWARDS from the option's market price
- IV of 10% = market prices 68% chance of stock moving ±10% in 1 year
- 2 standard deviations (95% probability) = ±20% in 1 year
- Formula to convert to X days: IV × √(X/252)

**Deep ITM options have artificially high IV** (don't use for IV measurement)
**Use ATM options** to measure true market expected IV.

**After earnings:** IV always CRASHES (IV crush). Options become cheap immediately.
**Before earnings:** IV always INFLATES. Options become expensive.

---

### OPTION PRICE = INTRINSIC VALUE + EXTRINSIC VALUE

**Intrinsic Value:** What you'd get if you exercised right now
- Call: max(0, Stock Price - Strike)
- Put: max(0, Strike - Stock Price)

**Extrinsic Value (Time Value):** Option price - Intrinsic Value
- This is what sellers collect and buyers pay
- Decays to zero by expiration (Theta)
- Accelerates after 35 DTE (the hockey stick)

**Deep ITM options:** Mostly intrinsic value. Manage like stock.
**OTM options:** All extrinsic value. Sellers want this to decay to zero.

---

### GLOSSARY (Hebrew-English quick reference)

- קול = Call | פוט = Put
- שער מימוש = Strike Price
- תאריך פקיעה = Expiration Date
- פרמיה = Premium
- ערך פנימי = Intrinsic Value
- ערך חיצוני = Extrinsic Value (Time Value)
- מחוץ לכסף = OTM (Out of The Money)
- בתוך הכסף = ITM (In The Money)
- בכסף = ATM (At The Money)
- דלתא = Delta | גאמא = Gamma | תטא = Theta | וגה = Vega
- השמה מוקדמת = Early Assignment
- נכס הבסיס = Underlying Asset
- גודל חוזה = Contract Size (always 100 shares for US stocks)

---

### AGENT INSTRUCTIONS — HOW TO USE THIS KNOWLEDGE

**When Haim asks about a trade:**
1. First identify: What is the market direction? (bullish/bearish/neutral)
2. Check: What is the IV Rank? (sell high, buy low)
3. Check: Is there earnings inside the expiration window?
4. Select strategy from the matrix above
5. Calculate: Expected Move, appropriate strikes (Delta 0.15-0.25 for selling)
6. State: Credit collected, max loss, breakeven, probability of profit
7. State: Management rules BEFORE entry (50% profit target, 2× stop loss, 21 DTE review, 10 DTE exit)

**Never recommend:**
- Naked calls or puts without explicitly noting the unlimited risk
- Strategies with earnings inside the cycle (unless intentional earnings play)
- Options with bid-ask spread > 10% of mid-price
- 0DTE strategies for part-time traders
- Far OTM long options as "lottery tickets"

**Always remind:**
- The Wheel only works on stocks you'd happily own
- Defined risk ≠ small risk (10 condors × $300 = $3,000 real exposure)
- Time decay works FOR sellers, AGAINST buyers — every single day

---

*Source: RanOptions course + "מאפס למאה באופציות" 109 pages + JasonL_Capital guides + TheOptionPremium.com*
*Learned and integrated: April 2026*

---

## 📚 WHEEL STRATEGY DEEP KNOWLEDGE
### Source: wheelstrategyoptions.com (April 2026)

---

### THE WHEEL STRATEGY — COMPLETE FRAMEWORK

**Core principle:** Consistent income generation through a systematic CSP → CC cycle.
Works in ANY market condition because every outcome is planned in advance.

**Expected returns (realistic):** 1-3% per month on capital deployed = 12-36% annually.
Not 47% annualized every month — that's only possible with very high IV stocks.

**Best stocks for The Wheel:**
- Large cap, liquid, stable: AAPL, MSFT, NVDA, AMZN, TSLA, SPY, QQQ
- Market cap > $1B
- Average volume > 500K shares/day
- You must be willing to OWN them if assigned

**Never use The Wheel on:**
- Stocks you wouldn't want to own at any price
- Stocks with earnings within 14 days
- Low-priced stocks under $20 (too little premium for the risk)
- Stocks with market cap < $1B (liquidity risk)

---

### STRIKE PRICE SELECTION — COMPLETE FRAMEWORK

**The Strike Dilemma:** Too close to money = frequent assignment. Too far = not enough premium.

**Delta guide for CSP (selling puts):**

| Delta | Assignment Probability | Premium | Risk Level |
|-------|----------------------|---------|------------|
| -0.40 | ~40% | Highest | Aggressive |
| -0.30 | ~30% | High | Moderate |
| -0.20 | ~20% | Medium | Conservative (SWEET SPOT) |
| -0.10 | ~10% | Low | Very Safe |

**Sweet spot: Delta 0.20-0.30**
- High enough premium to be worthwhile
- Low enough probability to avoid constant assignment
- Good risk-reward balance

**4-Step Strike Selection Framework:**
1. Start with delta → filter to 0.20-0.30 range
2. Check technical support → prefer strikes at or BELOW support level
3. Calculate yield → minimum 1%+ monthly on capital deployed
4. Consider stock context → adjust for current volatility and conviction

**Adjusting for market conditions:**
- High Volatility (VIX > 22): Go more conservative (0.15-0.20 delta). Premiums are elevated so you can go further OTM while still collecting decent premium.
- Low Volatility (VIX < 15): May need 0.25-0.30 delta for acceptable premium. Or find stocks with elevated IV Rank.

**Example strike analysis (stock at $100):**

| Strike | Delta | Monthly Yield | Support? | Best Choice? |
|--------|-------|---------------|---------|-------------|
| $97.50 | -0.35 | 2.9% | No | Risky |
| $95.00 | -0.25 | 2.0% | Yes | ✅ Best |
| $92.50 | -0.18 | 1.3% | Yes | Conservative |
| $90.00 | -0.12 | 0.8% | Yes | Too little premium |

**Premium Yield Formula:**
- Monthly Yield = (Premium / Strike Price) × 100
- Annualized = Monthly Yield × (365 / DTE)

---

### AVOIDING VALUE TRAPS — CRITICAL KNOWLEDGE

**Key insight:** High premium is usually a WARNING SIGN, not an opportunity.
The market prices premium based on KNOWN RISK. High IV = high risk.

**Why premium is high — RED FLAGS:**

| High Premium Cause | What It Signals | Action |
|-------------------|-----------------|--------|
| Upcoming earnings | Binary event (gap risk) | AVOID unless intentional |
| FDA decision pending | Regulatory uncertainty | AVOID |
| Recent price crash | Potential continued decline | INVESTIGATE |
| Takeover rumor | Acquisition volatility | AVOID |
| Sector panic | Systemic risk | REDUCE SIZE |

**The Earnings Trap (most common mistake):**
- IV spikes 50-100%+ before earnings → premiums look "amazing"
- Reality: Stock can gap 10-20% overnight → your 0.20 delta put becomes deep ITM instantly
- No time to adjust or roll
- One bad trade wipes out months of gains
- RULE: Never sell puts expiring within 7 days of earnings (unless intentional earnings play)

**Fundamental Red Flags (check before ANY wheel trade):**
1. Negative earnings / unprofitable company
2. High debt levels (balance sheet stress)
3. Declining revenue (shrinking business)
4. Recent management turnover
5. SEC investigation or accounting concerns
6. Death cross (50MA < 200MA) on chart
7. Breaking major support levels
8. Short interest at 52-week high

**High IV Rank vs High IV — Know the difference:**
- High IV Rank (GOOD): IV elevated relative to its own history → opportunity to sell
- High IV absolute (POTENTIALLY BAD): Could signal known upcoming event → investigate why

**Quality Screening Filters (use ALL of these):**
1. Earnings date > 14 days away ✅
2. Positive earnings (P/E > 0) ✅
3. IV Rank > 30 (elevated but not extreme) ✅
4. Market cap > $1B ✅
5. Average volume > 500K ✅

**Position Concentration Rule:**
NEVER allocate more than 10-15% of options capital to a single stock.
"It can't happen to me" is what everyone says before the stock crashes 50%.

**Real Case Study (Value Trap):**
- Retail stock shows 8% monthly yield on puts (normal: 2%)
- Investigation: Earnings in 3 days + competitor just reported terrible + short interest at 52-week high + support already broken
- Outcome: Stock gaps down 25% after earnings
- Lesson: THE MARKET KNEW THE RISK. Premium was priced fairly for the actual danger.

---

### ROLLING OPTIONS — COMPLETE GUIDE

**What is Rolling:** Close current option + simultaneously open new one with different terms.
Execute as a SINGLE SPREAD ORDER to minimize slippage.

**Types of rolls:**

**Roll Out** (same strike, later expiration):
- Purpose: Collect more premium, extend duration
- When: Position working well, want to continue generating income
- Result: Usually a credit

**Roll Down** (lower strike — for puts):
- Purpose: Reduce assignment risk when stock is falling
- When: Stock dropped toward your strike, still bullish long-term
- Result: May be small debit or credit

**Roll Up** (higher strike — for puts):
- Purpose: More aggressive, more premium when stock rallied
- When: Stock rallied well above strike, want to reset
- Result: Usually a credit

**Roll Up and Out** (higher strike + later expiration — for calls):
- Purpose: Give stock room to run when it approaches your call strike
- When: Stock approaching call strike, don't want to give up shares
- Result: Often debit or small credit

**Roll Decision Matrix:**

| Position | Stock Movement | Action |
|----------|---------------|--------|
| Put sold | Stock down near strike | Roll Down and Out |
| Put sold | Stock up, low premium | Close OR Roll Up |
| Put sold | Stock flat | Let expire OR Roll Out |
| Call sold | Stock up near strike | Roll Up and Out |
| Call sold | Stock down | Let expire OR Roll Down |
| Call sold | Stock flat | Roll Out for more premium |

**When to Roll — YES:**
1. You still want to stay in the position (bullish on stock)
2. You can collect a credit (or at worst, tiny debit)
3. New position has good standalone risk/reward
4. Meaningful time value still available in new expiration

**When NOT to Roll — NO:**
1. You'd take a significant debit (better to just close)
2. Fundamentals have changed (stock no longer meets quality criteria)
3. Better opportunities exist elsewhere (opportunity cost)
4. You're "rolling forever" to avoid realizing a loss — DANGEROUS

**The "Never Close at a Loss" TRAP:**
Rolling endlessly to avoid realizing losses is DANGEROUS:
- Ties up capital in losing position
- Opportunity cost compounds
- Stock might never recover
- Leads to increasingly bad rolls

RULE: Set max 2-3 rolls OR a maximum loss threshold (e.g., 2× premium collected).
Then EXIT regardless, even at a loss.

**Roll Execution Tips:**
1. Use LIMIT ORDERS (not market orders)
2. Roll during regular market hours only
3. Don't roll too early — let theta decay work first (wait until 50% profit or 21 DTE)
4. Consider rolling at 50% profit to lock in gains and reset
5. Track ALL rolls for tax purposes

**Example — Put Roll:**
- Sold $50 put for $1.50, 30 DTE
- Stock drops to $49
- Action: Buy back $50 put for $2.50 (book $1.00 loss), sell $47.50 put with 45 DTE for $2.00
- Net debit: $0.50
- New breakeven: Lower strike, more time
- If $47.50 expires worthless: Total profit = $1.00 over 75 days

**Roll Tracking (for tax and performance):**
Keep running total of all premium collected across rolls to understand true position P&L.

---

### REAL SCREENER DATA — AAPL CSP (April 2026)

Current market data from wheelstrategyoptions.com:

**AAPL at $255.92:**
- 1,141 available CSP contracts
- Average IV: 7.5% (LOW — not ideal for selling)
- Peak IV: 30.7%
- Best contract: $250 strike, May 15, 39 DTE, Delta -0.37, $7.50 premium, 2.90% yield
- Rating: B

**Insight:** AAPL's IV of 7.5% average is VERY LOW. This means:
- CSP premiums are thin relative to capital required
- Better to look for stocks with higher IV Rank (> 30) for better premium
- AAPL is good for the Wheel when IV spikes to 20%+ (during market drops)

**Other top Wheel candidates:** MSFT, NVDA, AMZN, TSLA, SPY, QQQ

---

### AGENT INSTRUCTIONS — WHEEL STRATEGY SPECIFIC

**When Haim asks about a Wheel trade:**

1. First ask: "Is this a stock you'd happily own if assigned?"
2. Check: Earnings > 14 days away? (if not → flag as dangerous)
3. Check: IV Rank > 30? (if not → premium may not justify risk)
4. Check: Is it a quality company? (P/E > 0, Market cap > $1B)
5. Look for: Strike at or below key technical support level
6. Calculate: Monthly yield = (premium / strike) × 100 → target ≥ 1%
7. State: All 3 scenarios before entry

**Red flags to always check:**
- Unusually high IV → ASK WHY before recommending
- Earnings within cycle → DO NOT recommend CSP
- Breaking major support → warn before entry
- Stock below $20 → avoid (insufficient premium per dollar of risk)

**Rolling rules for Haim:**
- Roll when stock moves against you AND you're still bullish on the company
- Max 2-3 rolls per position
- Always collect credit on rolls when possible
- Set maximum loss threshold = 2× original premium collected

**Value trap warning trigger:**
If a stock shows > 2× its normal IV → always investigate WHY before recommending

---

*Source: wheelstrategyoptions.com — 19-lesson free course + screener data*
*Accessed: April 2026*

---

*Last updated: April 2026*
