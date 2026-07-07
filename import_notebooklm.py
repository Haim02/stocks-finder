"""
import_notebooklm.py — One-shot import of NotebookLM knowledge into MongoDB
============================================================================

For every notebook in Haim's NotebookLM library, asks NotebookLM to distill
its material into a dense knowledge document, then saves it into the agent's
`learned_knowledge` collection (the same store `/knowledge` and free_chat use).

Run locally (where `notebooklm login` was done):
    env\\Scripts\\python.exe import_notebooklm.py             # all notebooks
    env\\Scripts\\python.exe import_notebooklm.py --only gex  # title filter
    env\\Scripts\\python.exe import_notebooklm.py --force     # re-import all

Idempotent: notebooks already imported today are skipped unless --force.
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_notebooklm")

EXTRACTION_PROMPT = (
    "Create a dense, complete knowledge document of EVERYTHING important in this "
    "notebook, for use by an AI trading assistant. Include: (1) all key concepts "
    "and definitions, (2) every concrete trading rule, threshold, and number, "
    "(3) practical playbooks/setups step by step, (4) common mistakes and warnings. "
    "Use compact markdown bullets. Financial terms in English. "
    "Do not summarize superficially — extract the actual substance."
)


def import_all(only: str = "", force: bool = False) -> None:
    from app.services.notebooklm_service import list_notebooks, ask_notebook
    from app.services.memory_engine import MemoryEngine

    memory = MemoryEngine()
    if memory.knowledge_col is None:
        logger.error("MongoDB unavailable — aborting")
        sys.exit(1)

    notebooks = list_notebooks()
    if not notebooks:
        logger.error("No notebooks found — is `notebooklm login` valid?")
        sys.exit(1)

    logger.info("Found %d notebooks", len(notebooks))
    imported = skipped = failed = 0

    for i, nb in enumerate(notebooks, 1):
        title = nb["title"]
        if only and only.lower() not in title.lower():
            continue

        topic = f"NotebookLM — {title}"
        source = f"notebooklm:{nb['id']}"

        if not force:
            existing = memory.knowledge_col.find_one({"source": source})
            if existing and len(existing.get("content", "")) > 500:
                logger.info("[%d/%d] SKIP (already imported): %s", i, len(notebooks), title)
                skipped += 1
                continue

        logger.info("[%d/%d] Asking NotebookLM: %s ...", i, len(notebooks), title)
        result = ask_notebook(EXTRACTION_PROMPT, notebook_id=nb["id"])

        if not result or len(result.get("answer", "")) < 200:
            logger.warning("[%d/%d] FAILED or empty answer: %s", i, len(notebooks), title)
            failed += 1
            continue

        memory.save_knowledge(
            topic=topic,
            content=result["answer"],
            source=source,
            tags=["notebooklm"] + [w for w in title.lower().split() if len(w) > 3][:6],
        )
        logger.info(
            "[%d/%d] SAVED: %s (%d chars)",
            i, len(notebooks), title, len(result["answer"]),
        )
        imported += 1
        time.sleep(3)  # be gentle with NotebookLM

    logger.info("Done. imported=%d skipped=%d failed=%d", imported, skipped, failed)

    # Stamp the import so the agent knows its knowledge base freshness
    try:
        memory.update_profile({
            "notebooklm_last_import": datetime.now(timezone.utc).isoformat(),
            "notebooklm_notebook_count": len(notebooks),
        })
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import NotebookLM knowledge into MongoDB")
    parser.add_argument("--only", default="", help="Only notebooks whose title contains this text")
    parser.add_argument("--force", action="store_true", help="Re-import even if already imported")
    args = parser.parse_args()
    import_all(only=args.only, force=args.force)
