"""
orchestrator.py — Agent Orchestrator
======================================

Central manager for the 3-agent autonomous trading system.

Agent Timeline (Israel time, Mon–Fri):
  10:00  Agent 1 — Market Regime Analyst
  10:30  Agent 2 — Options Strategist (only if Agent 1 not RED)
  09:30–16:30 hourly — Agent 3 — Risk Manager
  16:45  Daily Summary — recap of the day

Data Flow:
  Agent 1 → MongoDB (market_regime_reports)
         → Agent 2 reads via get_latest_regime()
  Agent 2 → MongoDB (options_strategist_reports)
         → Agent 3 reads via get_todays_ideas()
  Agent 3 → MongoDB (open_positions)
         → Telegram alerts

The Orchestrator also:
  - Tracks agent run history in MongoDB (agent_run_log)
  - Sends a daily summary at 16:45
  - Provides /status command for health check
  - Handles failures: if Agent 1 fails → Agent 2 is skipped
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ── Run log entry ─────────────────────────────────────────────────────────────

@dataclass
class AgentRunResult:
    agent_name: str
    success: bool
    started_at: str
    finished_at: str
    duration_seconds: float
    error: Optional[str] = None
    summary: Optional[str] = None


# ── Orchestrator ──────────────────────────────────────────────────────────────

class AgentOrchestrator:
    """
    Manages the complete 3-agent pipeline.

    Usage in run_agent.py:
        from app.agent.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()

        scheduler.add_job(orchestrator.run_morning_pipeline, ...)
        scheduler.add_job(orchestrator.run_risk_check, ...)
        scheduler.add_job(orchestrator.run_daily_summary, ...)
    """

    def __init__(self):
        self._run_history: list[AgentRunResult] = []
        logger.info("AgentOrchestrator initialized")

    # ── Morning Pipeline (10:00 → 10:30) ─────────────────────────────────────

    def run_morning_pipeline(self) -> None:
        """
        Full morning pipeline: Agent 1 → Agent 2.
        Called at 10:00 AM Israel time.
        Agent 2 runs after a 2-minute buffer once Agent 1 completes.
        """
        logger.info("╔══════════════════════════════════════╗")
        logger.info("║  Morning Pipeline — START            ║")
        logger.info("╚══════════════════════════════════════╝")

        # Step 1: Agent 1 — Market Regime
        regime_result = self._run_agent_1()
        self._log_run(regime_result)

        if not regime_result.success:
            self._notify(
                "⚠️ *Orchestrator — שגיאה*\n\n"
                "Agent 1 נכשל — Agent 2 לא יופעל היום.\n"
                f"שגיאה: `{regime_result.error}`"
            )
            return

        # Read verdict
        from app.agent.market_regime_agent import get_latest_regime
        regime = get_latest_regime()
        verdict = regime.get("verdict", "YELLOW") if regime else "YELLOW"

        if verdict == "RED":
            logger.info("RED regime — skipping Agent 2")
            return

        # Step 2: Small buffer then Agent 2
        logger.info("Waiting 2 minutes before running Agent 2...")
        time.sleep(120)

        strategist_result = self._run_agent_2()
        self._log_run(strategist_result)

        if not strategist_result.success:
            self._notify(
                "⚠️ *Orchestrator — שגיאה*\n\n"
                f"Agent 2 נכשל: `{strategist_result.error}`"
            )

        logger.info("╔══════════════════════════════════════╗")
        logger.info("║  Morning Pipeline — DONE             ║")
        logger.info("╚══════════════════════════════════════╝")

    # ── Risk Check (hourly) ───────────────────────────────────────────────────

    def run_risk_check(self) -> None:
        """Run Agent 3 hourly check. Called every hour during market hours."""
        result = self._run_agent_3()
        self._log_run(result)

        if not result.success:
            logger.error("Agent 3 failed: %s", result.error)
            # Only alert after 3+ consecutive failures to avoid spam
            recent_failures = sum(
                1 for r in self._run_history[-6:]
                if r.agent_name == "Agent3_RiskManager" and not r.success
            )
            if recent_failures >= 3:
                self._notify(
                    "⚠️ *Orchestrator — Agent 3 כשלים חוזרים*\n\n"
                    f"Agent 3 נכשל {recent_failures} פעמים ברצף.\n"
                    f"שגיאה: `{result.error}`"
                )

    # ── Daily Summary (16:45) ─────────────────────────────────────────────────

    def run_daily_summary(self) -> None:
        """Send an end-of-day summary to Telegram. Called at 16:45 Israel time."""
        logger.info("Building daily summary...")

        today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        today_runs = [
            r for r in self._run_history
            if r.started_at.startswith(today_prefix)
        ]

        a1 = next((r for r in today_runs if r.agent_name == "Agent1_MarketRegime"), None)
        a2 = next((r for r in today_runs if r.agent_name == "Agent2_Strategist"), None)
        a3_runs = [r for r in today_runs if r.agent_name == "Agent3_RiskManager"]
        a3_alerts = self._get_todays_alert_count()

        from app.agent.risk_manager_agent import RiskManagerAgent
        positions_summary = RiskManagerAgent.get_open_positions_summary()

        from app.agent.options_strategist_agent import get_todays_ideas
        ideas = get_todays_ideas()

        a1_status = "✅" if (a1 and a1.success) else "❌"
        if not a2:
            a2_status = "⏭️ דולג (RED regime)"
        elif a2.success:
            a2_status = "✅"
        else:
            a2_status = "❌"
        a3_status = f"✅ {len(a3_runs)} ריצות, {a3_alerts} התראות"

        ideas_text = ""
        if ideas:
            tickers = [i.get("ticker", "?") for i in ideas]
            ideas_text = f"\n📋 עסקאות שהומלצו היום: {', '.join(tickers)}"

        msg = (
            f"📊 *סיכום יומי — {datetime.now().strftime('%d/%m/%Y')}*\n"
            f"{'━' * 30}\n\n"
            f"🧠 Agent 1 (Regime): {a1_status}\n"
            f"👨‍💼 Agent 2 (Strategist): {a2_status}\n"
            f"🕵️ Agent 3 (Risk): {a3_status}"
            f"{ideas_text}\n\n"
            f"{'━' * 30}\n"
            f"{positions_summary}\n\n"
            f"_מחר בשעה 10:00 האג'נטים יתחילו מחדש_"
        )

        self._notify(msg)
        logger.info("Daily summary sent")

    # ── Individual agent runners ──────────────────────────────────────────────

    def _run_agent_1(self) -> AgentRunResult:
        return self._run_safely(
            name="Agent1_MarketRegime",
            runner=lambda: (
                __import__(
                    "app.agent.market_regime_agent",
                    fromlist=["MarketRegimeAgent"],
                ).MarketRegimeAgent().run()
            ),
        )

    def _run_agent_2(self) -> AgentRunResult:
        return self._run_safely(
            name="Agent2_Strategist",
            runner=lambda: (
                __import__(
                    "app.agent.options_strategist_agent",
                    fromlist=["OptionsStrategistAgent"],
                ).OptionsStrategistAgent().run()
            ),
        )

    def _run_agent_3(self) -> AgentRunResult:
        return self._run_safely(
            name="Agent3_RiskManager",
            runner=lambda: (
                __import__(
                    "app.agent.risk_manager_agent",
                    fromlist=["RiskManagerAgent"],
                ).RiskManagerAgent().run()
            ),
        )

    def _run_safely(self, name: str, runner) -> AgentRunResult:
        """Run any agent safely, catching all exceptions."""
        started = datetime.utcnow()
        logger.info("Starting %s at %s", name, started.isoformat())
        try:
            runner()
            finished = datetime.utcnow()
            duration = (finished - started).total_seconds()
            logger.info("%s completed in %.1fs", name, duration)
            return AgentRunResult(
                agent_name=name,
                success=True,
                started_at=started.isoformat(),
                finished_at=finished.isoformat(),
                duration_seconds=duration,
            )
        except Exception as e:
            finished = datetime.utcnow()
            duration = (finished - started).total_seconds()
            error_msg = f"{type(e).__name__}: {e}"
            logger.exception("%s FAILED after %.1fs", name, duration)
            return AgentRunResult(
                agent_name=name,
                success=False,
                started_at=started.isoformat(),
                finished_at=finished.isoformat(),
                duration_seconds=duration,
                error=error_msg,
            )

    # ── Health check ──────────────────────────────────────────────────────────

    def get_status(self) -> str:
        """
        Returns a Hebrew status report of all agents.
        Used by /status Telegram command.
        """
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()

            # Latest Agent 1 report
            a1_doc = db["market_regime_reports"].find_one(sort=[("timestamp", -1)])
            if a1_doc:
                a1_time = a1_doc.get("timestamp", "?")[:16].replace("T", " ")
                a1_verdict = a1_doc.get("verdict", "?")
                verdict_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(a1_verdict, "⚪")
                a1_line = f"{verdict_emoji} Regime: *{a1_verdict}* (עודכן: {a1_time})"
            else:
                a1_line = "⚠️ Agent 1: אין נתונים"

            # Latest Agent 2 report
            a2_doc = db["options_strategist_reports"].find_one(sort=[("timestamp", -1)])
            if a2_doc:
                a2_time = a2_doc.get("timestamp", "?")[:16].replace("T", " ")
                n_ideas = len(a2_doc.get("trade_ideas", []))
                a2_line = f"👨‍💼 Strategist: *{n_ideas} עסקאות* (עודכן: {a2_time})"
            else:
                a2_line = "⚠️ Agent 2: אין נתונים"

            # Open positions count
            n_open = db["open_positions"].count_documents(
                {"status": {"$nin": ["closed"]}}
            )
            a3_line = f"🕵️ Risk Manager: עוקב אחרי *{n_open} פוזיציות*"

            # Recent run history
            recent = self._run_history[-5:]
            if recent:
                history_lines = [
                    f"  {'✅' if r.success else '❌'} {r.agent_name} "
                    f"— {r.started_at[11:16]} ({r.duration_seconds:.0f}s)"
                    for r in reversed(recent)
                ]
                history_text = "\n".join(history_lines)
            else:
                history_text = "  אין היסטוריה עדיין"

            return (
                f"🤖 *מצב הסוכנים*\n"
                f"{'━' * 28}\n\n"
                f"{a1_line}\n"
                f"{a2_line}\n"
                f"{a3_line}\n\n"
                f"⏱️ *ריצות אחרונות:*\n"
                f"{history_text}\n\n"
                f"📅 *לו\"ז:*\n"
                f"  🕙 10:00 — Agent 1\n"
                f"  🕥 10:30 — Agent 2\n"
                f"  🔁 כל שעה — Agent 3\n"
                f"  🕔 16:45 — סיכום יומי"
            )

        except Exception as e:
            logger.error("Status check failed: %s", e)
            return f"⚠️ שגיאה בשליפת הסטטוס: {e}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log_run(self, result: AgentRunResult) -> None:
        self._run_history.append(result)
        # Keep only last 50 entries in memory
        if len(self._run_history) > 50:
            self._run_history = self._run_history[-50:]

        # Also persist to MongoDB
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            db["agent_run_log"].insert_one({
                "agent_name": result.agent_name,
                "success": result.success,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "duration_seconds": result.duration_seconds,
                "error": result.error,
            })
        except Exception:
            pass  # non-fatal

    def _notify(self, message: str) -> None:
        try:
            from app.agent.telegram_bot import notify_trade
            notify_trade(message)
        except Exception as e:
            logger.error("Orchestrator Telegram notification failed: %s", e)

    def _get_todays_alert_count(self) -> int:
        try:
            from app.data.mongo_client import MongoDB
            db = MongoDB.get_db()
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            return db["open_positions"].count_documents({
                "last_alerted": {"$gte": today}
            })
        except Exception:
            return 0
