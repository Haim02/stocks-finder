"""
notebooklm_service.py — Live access to Haim's Google NotebookLM library
========================================================================

Wraps the `notebooklm` CLI (teng-lin/notebooklm-py) so the agent can query
the full source material behind the knowledge base — 17+ notebooks covering
GEX/dealer hedging, SpotGamma, Unusual Whales, Delta Footprint, ATAS,
CVD/IV, futures, and the SPX 0DTE course.

Requirements (already satisfied on Haim's machine):
  pip install "notebooklm-py[browser]"
  notebooklm login            # auth stored in ~/.notebooklm (persists)

Degrades gracefully: if the CLI or auth is missing (e.g. Railway container
without a mounted ~/.notebooklm), every function returns None/[] and the
agent falls back to the imported knowledge in MongoDB.
"""

import json
import logging
import os
import shutil
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)

_ASK_TIMEOUT = 150          # NotebookLM answers can take 30-60s
_LIST_TTL = 3600
_list_cache: dict = {}


def _find_cli() -> Optional[str]:
    """Locate the notebooklm executable across platforms."""
    path = shutil.which("notebooklm")
    if path:
        return path
    # Windows user-site install (pip install --user)
    appdata = os.getenv("APPDATA", "")
    for candidate in (
        os.path.join(appdata, "Python", "Python313", "Scripts", "notebooklm.exe"),
        os.path.join(appdata, "Python", "Scripts", "notebooklm.exe"),
    ):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def is_available() -> bool:
    return _find_cli() is not None


def _run_cli(args: list, timeout: int = _ASK_TIMEOUT) -> Optional[str]:
    cli = _find_cli()
    if not cli:
        logger.debug("notebooklm CLI not found")
        return None
    try:
        result = subprocess.run(
            [cli] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning("notebooklm %s failed: %s", args[0], (result.stderr or "")[:300])
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.warning("notebooklm %s timed out after %ds", args[0], timeout)
        return None
    except Exception as e:
        logger.warning("notebooklm CLI error: %s", e)
        return None


def list_notebooks() -> list[dict]:
    """All notebooks as [{'id', 'title'}], cached for an hour."""
    cached = _list_cache.get("notebooks")
    if cached and time.time() - cached[1] < _LIST_TTL:
        return cached[0]

    out = _run_cli(["list", "--json"], timeout=60)
    if not out:
        return []
    try:
        data = json.loads(out)
        notebooks = [
            {"id": nb["id"], "title": nb.get("title") or "(ללא שם)"}
            for nb in data.get("notebooks", [])
        ]
        _list_cache["notebooks"] = (notebooks, time.time())
        return notebooks
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("notebooklm list parse failed: %s", e)
        return []


# Keyword → notebook-title hints for picking the right notebook per question
_TOPIC_HINTS = {
    "footprint": "footprint", "delta": "footprint",
    "atas": "atas", "heatmap": "atas",
    "cvd": "cvd", "iv": "cvd",
    "spotgamma": "spotgamma", "trace": "trace", "hiro": "spotgamma",
    "gex": "gamma", "gamma": "gamma", "dealer": "gamma",
    "unusual": "unusual whales", "whales": "unusual whales",
    "periscope": "periscope", "greek": "periscope",
    "0dte": "0dte", "spx": "0dte",
    "futures": "futures", "חוזים": "futures", "מינוף": "futures",
    "orderflow": "orderflow", "course": "course", "קורס": "course",
    "quant": "quant",
}


def pick_notebook(question: str) -> Optional[dict]:
    """Choose the most relevant notebook for a question by title matching."""
    notebooks = list_notebooks()
    if not notebooks:
        return None

    q = question.lower()
    scores: dict[str, int] = {}
    for nb in notebooks:
        title = nb["title"].lower()
        score = 0
        for kw, hint in _TOPIC_HINTS.items():
            if kw in q and hint in title:
                score += 2
        # direct word overlap between question and title
        score += sum(1 for w in q.split() if len(w) > 3 and w in title)
        scores[nb["id"]] = score

    best = max(notebooks, key=lambda nb: scores.get(nb["id"], 0))
    if scores.get(best["id"], 0) == 0:
        # No signal — default to the main SPX 0DTE GEX notebook if present
        for nb in notebooks:
            if "0dte" in nb["title"].lower():
                return nb
        return notebooks[0]
    return best


def ask_notebook(question: str, notebook_id: Optional[str] = None) -> Optional[dict]:
    """
    Ask NotebookLM a question. Returns {'answer', 'notebook_title'} or None.
    If notebook_id is omitted, the most relevant notebook is picked by title.
    """
    title = ""
    if not notebook_id:
        nb = pick_notebook(question)
        if not nb:
            return None
        notebook_id, title = nb["id"], nb["title"]

    out = _run_cli(["ask", "-n", notebook_id, "--json", question])
    if not out:
        return None

    answer = None
    try:
        data = json.loads(out)
        answer = data.get("answer") or data.get("text") or data.get("response")
    except json.JSONDecodeError:
        # Plain-text fallback: strip CLI chrome lines
        lines = [
            ln for ln in out.splitlines()
            if ln.strip() and not ln.startswith(
                ("Matched:", "Continuing", "Resumed", "Started", "Answer:")
            )
        ]
        answer = "\n".join(lines).strip() or None

    if not answer:
        return None
    return {"answer": answer, "notebook_title": title, "notebook_id": notebook_id}


def format_nlm_hebrew(result: dict, question: str) -> str:
    """Format a NotebookLM answer for Telegram."""
    title = result.get("notebook_title") or ""
    header = f"📓 *NotebookLM — {title}*" if title else "📓 *NotebookLM*"
    return (
        f"{header}\n"
        f"❓ {question[:150]}\n"
        f"──────────────────────────\n"
        f"{result['answer'][:3500]}"
    )
