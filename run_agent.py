"""
Autonomous Trading Agent — Entry Point
=======================================
Starts the autonomous Hedge Fund Manager agent for the daily options workflow.

The agent operates via a ReAct loop (Reason → Act → Observe → Reason ...):
  1. Checks market conditions (VIX, SPX, FRED macro)
  2. Decides which direction to scan based on macro regime
  3. Scans Finviz, filters by XGBoost, checks 4-day cooldown
  4. Runs deep fundamental + institutional analysis on top candidates
  5. Builds 0DTE SPX iron condor and stock credit spreads
  6. Compiles and sends the Daily Options Brief — ONLY if quality ≥ 60
  7. Aborts cleanly when conditions are unfavorable

No manual pipeline decisions are made in this file.
All reasoning and tool-selection is done autonomously by GPT-4o.

Usage:
    python run_agent.py              # run once now
    python run_agent.py --daemon     # scheduler (16:45 Israel) + Telegram bot

Schedule: runs daily at 16:45 Israel time (= 09:45 US/Eastern), Mon–Fri.
"""

import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# One-shot agent run
# ══════════════════════════════════════════════════════════════════════════════

def run_once() -> None:
    """Execute a single agent workflow and log the result."""
    start = datetime.now()
    logger.info("╔══════════════════════════════════════╗")
    logger.info("║   Autonomous Trading Agent — Start   ║")
    logger.info("╚══════════════════════════════════════╝")

    try:
        from app.agent.trading_agent import TradingAgent

        agent   = TradingAgent()
        summary = agent.run()

        elapsed = (datetime.now() - start).total_seconds()
        logger.info("╔══════════════════════════════════════╗")
        logger.info("║      Agent Workflow Complete         ║")
        logger.info("╚══════════════════════════════════════╝")
        logger.info("Elapsed: %.1fs", elapsed)
        logger.info("Summary:\n%s", summary)

        # Print the tool call trace for easy debugging
        log = agent.tool_call_log
        if log:
            logger.info("── Tool call trace (%d calls) ──", len(log))
            for i, entry in enumerate(log, 1):
                status = "✓" if "error" not in entry["result"] else "✗"
                logger.info(
                    "  %2d. %s %s  args=%s",
                    i, status, entry["tool"],
                    str(entry["args"])[:80],
                )

        # Telegram notification with the closing summary
        try:
            from app.agent.telegram_bot import notify_trade
            short = summary[:600] if summary else "הסוכן השלים את הריצה היומית."
            notify_trade(f"🤖 *סוכן יומי — הושלם*\n\n{short}")
        except Exception:
            pass  # non-fatal

    except KeyboardInterrupt:
        logger.info("Agent interrupted by user.")
    except Exception:
        logger.exception("Agent raised an unhandled exception")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# Daemon mode — APScheduler + Telegram bot
# ══════════════════════════════════════════════════════════════════════════════

def run_daemon() -> None:
    """
    Start APScheduler (daily 09:45 EST) AND the Telegram bot in daemon mode.

    The scheduler fires run_once() every weekday at 09:45 US/Eastern.
    The Telegram bot runs in the main thread (blocking).
    The scheduler runs in a background thread.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error(
            "APScheduler not installed. Run: pip install apscheduler"
        )
        sys.exit(1)

    try:
        from app.agent.telegram_bot import run_bot
    except ImportError:
        logger.error(
            "python-telegram-bot not installed. Run: pip install python-telegram-bot"
        )
        sys.exit(1)

    # ── Scheduler ──────────────────────────────────────────────────────────
    # 16:45 Asia/Jerusalem = 09:45 US/Eastern (both timezones shift together
    # for DST, so this is always correct regardless of season)
    SCAN_TZ   = "Asia/Jerusalem"
    SCAN_HOUR = 16
    SCAN_MIN  = 45

    scheduler = BackgroundScheduler(timezone=SCAN_TZ)
    scheduler.add_job(
        run_once,
        trigger=CronTrigger(
            day_of_week="mon-fri",  # market days only
            hour=SCAN_HOUR,
            minute=SCAN_MIN,
            timezone=SCAN_TZ,
        ),
        id="daily_agent_run",
        name=f"Daily Options Agent ({SCAN_HOUR:02d}:{SCAN_MIN:02d} Israel)",
        replace_existing=True,
        misfire_grace_time=300,  # allow up to 5 min late start
    )
    scheduler.start()

    next_run = scheduler.get_job("daily_agent_run").next_run_time
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║   Daemon Mode — Scheduler + Telegram Bot     ║")
    logger.info("╚══════════════════════════════════════════════╝")
    logger.info("Scheduled daily at %02d:%02d %s (Mon–Fri)", SCAN_HOUR, SCAN_MIN, SCAN_TZ)
    logger.info("Next run: %s", next_run)

    # ── Telegram bot (blocks until Ctrl-C) ────────────────────────────────
    try:
        run_bot()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Daemon stopping...")
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        run_once()


if __name__ == "__main__":
    main()
