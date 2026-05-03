"""
Autonomous Trading Agent — Production Entry Point
==================================================
Starts BOTH the Telegram bot AND the APScheduler in a single process.

Default mode (no flags): DAEMON — runs forever on Railway/VPS.
  - Telegram bot responds to /scan, /status, /options, /analyze
  - APScheduler jobs (Asia/Jerusalem, Mon–Fri):
      10:00  morning_pipeline  — Agent 1 (MarketRegime) + Agent 2 (OptionsStrategist)
      09:30–16:30  risk_check  — Agent 3 (RiskManager) every hour
      16:45  daily_summary     — Orchestrator end-of-day summary

Single-run mode (--once): execute one agent cycle and exit.
  Used for manual testing or cron-based orchestration.

Usage:
    python run_agent.py          # daemon: scheduler + Telegram bot (Railway default)
    python run_agent.py --once   # single options-agent run, then exit
"""

import argparse
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_orchestrator = None  # set in run_daemon() once AgentOrchestrator is created


# ══════════════════════════════════════════════════════════════════════════════
# One-shot agent run
# ══════════════════════════════════════════════════════════════════════════════

def run_once() -> None:
    """Execute a single options-agent workflow and log the result."""
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

        try:
            from app.agent.telegram_bot import notify_trade
            short = (summary or "הסוכן השלים את הריצה היומית.")[:600]
            notify_trade(f"🤖 *סוכן יומי — הושלם*\n\n{short}")
        except Exception:
            pass  # non-fatal

    except KeyboardInterrupt:
        logger.info("Agent interrupted by user.")
    except Exception:
        logger.exception("Agent raised an unhandled exception")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# Daemon mode — APScheduler + Telegram bot (production default)
# ══════════════════════════════════════════════════════════════════════════════

def run_daemon() -> None:
    """
    Production mode: start APScheduler + Telegram bot in one process.

    Scheduler jobs:
      - morning_pipeline : 10:00 Israel (Agent 1 + Agent 2)
      - risk_check       : hourly 09:30–16:30 Israel (Agent 3)
      - daily_summary    : 16:45 Israel
    Telegram: responds to /scan /status /options /analyze (blocking main thread).
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    try:
        from app.agent.telegram_bot import run_bot
    except ImportError:
        logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        sys.exit(1)

    SCAN_TZ = "Asia/Jerusalem"

    # Ensure MongoDB indexes on startup (idempotent)
    try:
        from app.data.mongo_client import MongoDB
        MongoDB.ensure_indexes()
    except Exception as e:
        logger.warning("MongoDB ensure_indexes failed on startup: %s", e)

    scheduler = BackgroundScheduler(timezone=SCAN_TZ)

    global _orchestrator
    from app.agent.orchestrator import AgentOrchestrator
    _orchestrator = AgentOrchestrator()

    # Agent 1 + Agent 2 morning pipeline (10:00 Israel)
    scheduler.add_job(
        _orchestrator.run_morning_pipeline,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=10,
            minute=0,
            timezone=SCAN_TZ,
        ),
        id="morning_pipeline",
        name="Morning Pipeline — Agent 1 + Agent 2 (10:00 Israel)",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Morning pipeline scheduled: 10:00 Israel time (Mon–Fri)")

    # Agent 3 — Risk Manager (hourly 09:30–16:30 Israel)
    scheduler.add_job(
        _orchestrator.run_risk_check,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-16",
            minute=30,
            timezone=SCAN_TZ,
        ),
        id="risk_check",
        name="Agent 3 — Risk Manager (hourly 09:30–16:30)",
        replace_existing=True,
        misfire_grace_time=120,
    )
    logger.info("Agent 3 scheduled: every hour 09:30–16:30 Israel time (Mon–Fri)")

    # Daily summary (16:45 Israel)
    scheduler.add_job(
        _orchestrator.run_daily_summary,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=16,
            minute=45,
            timezone=SCAN_TZ,
        ),
        id="daily_summary",
        name="Daily Summary (16:45 Israel)",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Daily summary scheduled: 16:45 Israel time (Mon–Fri)")

    # News Alert — every 15 min during US market hours (16:00–23:00 Israel)
    try:
        from app.services.news_alert_engine import run_news_scan_sync
        scheduler.add_job(
            run_news_scan_sync,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour="16-22",
                minute="*/15",
                timezone=SCAN_TZ,
            ),
            id="news_alert_scan",
            name="News Alert Scan (every 15min, 16:00–23:00 Israel)",
            replace_existing=True,
            misfire_grace_time=120,
        )
        logger.info("News alert scan scheduled: every 15min during 16:00–23:00 Israel (Mon–Fri)")

        # Pre-market scan (15:30 Israel = 08:30 ET)
        scheduler.add_job(
            run_news_scan_sync,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=15,
                minute=30,
                timezone=SCAN_TZ,
            ),
            id="news_alert_premarket",
            name="News Alert Pre-Market (15:30 Israel)",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info("News alert pre-market scan scheduled: 15:30 Israel time (Mon–Fri)")
    except ImportError:
        logger.warning("news_alert_engine not available — news alert jobs skipped")

    # ── Smart Alert System v2 — every 2 hours, 10:00-22:00 Israel ───────────
    try:
        from app.services.live_monitor import (
            run_2hour_scan_sync,
            run_morning_briefing_sync,
            run_evening_summary_sync,
        )

        # Remove old jobs if they exist (upgrade from v1)
        for old_job in ["live_monitor_15min", "web_crawler_30min",
                        "news_alert_scan", "premarket_news_scan"]:
            try:
                scheduler.remove_job(old_job)
            except Exception:
                pass

        # Every 2 hours, Mon-Fri, 10:00-22:00 Israel time
        scheduler.add_job(
            run_2hour_scan_sync,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour="10,12,14,16,18,20,22",
                minute=0,
                timezone=SCAN_TZ,
            ),
            id="smart_scan_2h",
            name="Smart Alert Scan — 2h (10:00–22:00 Israel)",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Morning briefing (09:00 Israel)
        scheduler.add_job(
            run_morning_briefing_sync,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=9,
                minute=0,
                timezone=SCAN_TZ,
            ),
            id="morning_briefing",
            name="Morning Briefing (09:00 Israel)",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Evening summary (22:30 Israel)
        scheduler.add_job(
            run_evening_summary_sync,
            trigger=CronTrigger(
                day_of_week="mon-fri",
                hour=22,
                minute=30,
                timezone=SCAN_TZ,
            ),
            id="evening_summary",
            name="Evening Summary (22:30 Israel)",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info("Smart alert system v2 scheduled: 2h scans + morning/evening briefings")
    except ImportError:
        logger.warning("live_monitor not available — smart alert jobs skipped")

    scheduler.start()

    next_run = scheduler.get_job("morning_pipeline").next_run_time
    env_label = os.getenv("RAILWAY_ENVIRONMENT", "local")
    logger.info("╔══════════════════════════════════════════════╗")
    logger.info("║   Daemon Mode — Scheduler + Telegram Bot     ║")
    logger.info("╚══════════════════════════════════════════════╝")
    logger.info("Environment : %s", env_label)
    logger.info("Timezone    : %s (Mon–Fri)", SCAN_TZ)
    logger.info("Next run    : %s", next_run)

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

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Autonomous Trading Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python run_agent.py         # daemon mode (Railway production)\n"
            "  python run_agent.py --once  # single run and exit\n"
        ),
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run the options agent once and exit (no scheduler or Telegram bot)",
    )
    # Keep --daemon as a no-op alias so old invocations don't break
    p.add_argument("--daemon", action="store_true", help=argparse.SUPPRESS)
    return p


def main() -> None:
    args = _build_parser().parse_args()
    if args.once:
        run_once()
    else:
        run_daemon()   # default: daemon (scheduler + Telegram)


if __name__ == "__main__":
    main()
