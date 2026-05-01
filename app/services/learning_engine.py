"""
learning_engine.py — Universal Learning Engine
===============================================

The agent can learn from ANY source:
1. URLs — reads any webpage and extracts key information
2. PDFs — extracts text and learns from documents (Claude Vision)
3. Images — reads charts, screenshots, financial statements
4. Plain text — direct knowledge input via /learn command
5. YouTube — gets transcript and key points (via Perplexity)
6. X/Twitter threads — captures viral trading insights
7. GitHub repos — reads README and key files

All learned knowledge is saved to MongoDB and
used automatically in future conversations.
"""

import base64
import logging
import os
import re
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")


class LearningEngine:
    """Handles learning from all types of content."""

    def __init__(self):
        try:
            from app.services.memory_engine import MemoryEngine
            self.memory = MemoryEngine()
        except Exception as e:
            logger.warning("LearningEngine: memory unavailable: %s", e)
            self.memory = None

    # ── URL Learning ──────────────────────────────────────────────────────────

    def learn_from_url(self, url: str) -> dict:
        """
        Learn from any URL.
        Handles: articles, GitHub repos, financial sites, YouTube, X/Twitter.
        """
        url_type = self._detect_url_type(url)

        if url_type == "youtube":
            return self._learn_from_youtube(url)
        elif url_type == "github":
            return self._learn_from_github(url)
        elif url_type == "twitter":
            return self._learn_from_twitter(url)
        elif url_type == "pdf":
            return self._learn_from_pdf_url(url)
        else:
            return self._learn_from_webpage(url)

    def _detect_url_type(self, url: str) -> str:
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "github.com" in url_lower:
            return "github"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        elif url_lower.endswith(".pdf"):
            return "pdf"
        return "webpage"

    def _learn_from_webpage(self, url: str) -> dict:
        try:
            content = self._fetch_url_direct(url)

            if not content or len(content) < 100:
                content = self._fetch_via_perplexity(
                    f"Provide a comprehensive summary of the content at: {url}. "
                    f"Include all key information, facts, strategies, and insights."
                )

            if not content:
                return {"success": False, "error": "לא הצלחתי לקרוא את הקישור"}

            knowledge = self._extract_knowledge_with_claude(content, url)
            topic = self._generate_topic(url, content)

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source=url)

            return {
                "success": True,
                "topic": topic,
                "summary": knowledge[:500],
                "chars_saved": len(knowledge),
                "source": url,
            }

        except Exception as e:
            logger.error("Webpage learning failed for %s: %s", url, e)
            return {"success": False, "error": str(e)}

    def _learn_from_youtube(self, url: str) -> dict:
        try:
            content = self._fetch_via_perplexity(
                f"What are the main content, key lessons, and important trading/financial insights "
                f"from this YouTube video: {url}? Provide a detailed summary."
            )
            if not content:
                return {"success": False, "error": "לא הצלחתי לקרוא את הסרטון"}

            topic = f"YouTube: {url.split('=')[-1][:20]}"
            knowledge = self._extract_knowledge_with_claude(content, url)

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source=url)

            return {
                "success": True,
                "topic": topic,
                "summary": knowledge[:500],
                "chars_saved": len(knowledge),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _learn_from_github(self, url: str) -> dict:
        try:
            # Try to fetch raw README
            raw_url = url.replace("github.com", "raw.githubusercontent.com")
            if not raw_url.endswith(".md"):
                raw_url = raw_url.rstrip("/") + "/main/README.md"
            content = self._fetch_url_direct(raw_url)

            if not content:
                content = self._fetch_via_perplexity(
                    f"What does this GitHub repository do? Key features, installation, use cases: {url}"
                )

            topic = url.rstrip("/").split("/")[-1][:40] or "GitHub Repo"
            knowledge = self._extract_knowledge_with_claude(content or "", url)

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source=url)

            return {
                "success": True,
                "topic": topic,
                "summary": knowledge[:500],
                "chars_saved": len(knowledge),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _learn_from_twitter(self, url: str) -> dict:
        try:
            content = self._fetch_via_perplexity(
                f"What are the main insights and key points from this X/Twitter thread: {url}? "
                f"Include any trading strategies, market insights, or financial information."
            )
            if not content:
                return {"success": False, "error": "לא הצלחתי לקרוא את הפוסט"}

            topic = f"X/Twitter: {url.rstrip('/').split('/')[-1][:20]}"
            knowledge = self._extract_knowledge_with_claude(content, url)

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source=url)

            return {
                "success": True,
                "topic": topic,
                "summary": knowledge[:500],
                "chars_saved": len(knowledge),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _learn_from_pdf_url(self, url: str) -> dict:
        try:
            import requests
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return self.learn_from_pdf_bytes(resp.content, source=url)
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── PDF Learning ──────────────────────────────────────────────────────────

    def learn_from_pdf_bytes(self, pdf_bytes: bytes, source: str = "PDF") -> dict:
        """Learn from PDF bytes using Claude's document reading capability."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            b64_pdf = base64.standard_b64encode(pdf_bytes).decode("utf-8")

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": b64_pdf,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Read this document carefully and extract ALL key information. "
                                    "Include: main topics, strategies, rules, formulas, examples, "
                                    "and actionable insights. Format as structured knowledge. "
                                    "This is for an options trading AI — focus on trading-relevant info. "
                                    "Write in Hebrew, keep technical terms in English."
                                ),
                            },
                        ],
                    }
                ],
            )

            knowledge = response.content[0].text.strip()
            topic = f"PDF: {source.split('/')[-1][:40]}"

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source=source)

            return {
                "success": True,
                "topic": topic,
                "summary": knowledge[:500],
                "chars_saved": len(knowledge),
                "pages_read": "entire document",
            }

        except Exception as e:
            logger.warning("Claude PDF reading failed, falling back: %s", e)
            return self._pdf_fallback(pdf_bytes, source)

    def _pdf_fallback(self, pdf_bytes: bytes, source: str) -> dict:
        """Fallback PDF reading via pypdf (text extraction only)."""
        try:
            import io
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            text = "\n".join(
                page.extract_text() for page in reader.pages[:20]
            )

            if not text.strip():
                return {"success": False, "error": "לא הצלחתי לחלץ טקסט מהPDF"}

            knowledge = self._extract_knowledge_with_claude(text[:5000], source)
            topic = f"PDF: {source.split('/')[-1][:40]}"

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source=source)

            return {
                "success": True,
                "topic": topic,
                "summary": knowledge[:500],
                "chars_saved": len(knowledge),
            }
        except ImportError:
            return {"success": False, "error": "pypdf לא מותקן — הרץ: pip install pypdf"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Image Learning ────────────────────────────────────────────────────────

    def learn_from_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        context: str = "",
    ) -> dict:
        """
        Analyze image using Claude Vision.
        Handles: charts, screenshots, financial statements, trading setups.
        """
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            b64_img = base64.standard_b64encode(image_bytes).decode("utf-8")

            prompt = (
                "Analyze this image carefully and provide detailed insights in Hebrew "
                "(keep financial/technical terms in English).\n\n"
                "• Trading chart: identify trend, key levels, patterns, indicators\n"
                "• Financial statement: extract key numbers and metrics\n"
                "• Trading setup: explain the setup and entry/exit rules\n"
                "• Options chain screenshot: identify IV, strikes, expiration, spread opportunities\n"
                "• Platform screenshot: identify what's shown and key data points"
            )
            if context:
                prompt += f"\n\nUser context: {context}"

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64_img,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )

            analysis = response.content[0].text.strip()

            saved = False
            if len(analysis) > 100 and self.memory:
                topic = f"תמונה: {context[:30]}" if context else f"Image {datetime.now().strftime('%d/%m %H:%M')}"
                self.memory.save_knowledge(topic, analysis, source="image")
                saved = True

            return {
                "success": True,
                "analysis": analysis,
                "saved_to_memory": saved,
            }

        except Exception as e:
            logger.error("Image learning failed: %s", e)
            return {"success": False, "error": str(e)}

    # ── Text Learning ─────────────────────────────────────────────────────────

    def learn_from_text(self, topic: str, content: str) -> dict:
        """Learn from direct text input."""
        try:
            knowledge = self._extract_knowledge_with_claude(content, "user input")

            if self.memory:
                self.memory.save_knowledge(topic, knowledge, source="user")

            return {
                "success": True,
                "topic": topic,
                "chars_saved": len(knowledge),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Helper Methods ────────────────────────────────────────────────────────

    def _fetch_url_direct(self, url: str) -> str:
        """Try to fetch URL content directly."""
        try:
            import requests
            from bs4 import BeautifulSoup
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                return "\n".join(lines[:200])
        except Exception:
            pass
        return ""

    def _fetch_via_perplexity(self, query: str) -> str:
        """Fetch content via Perplexity when direct fetch fails."""
        if not PERPLEXITY_API_KEY:
            return ""
        try:
            import requests
            resp = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {PERPLEXITY_API_KEY}"},
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": "Provide comprehensive, detailed information."},
                        {"role": "user", "content": query},
                    ],
                    "max_tokens": 800,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
        return ""

    def _extract_knowledge_with_claude(self, content: str, source: str) -> str:
        """Use Claude to extract and structure key knowledge from content."""
        if not content or len(content) < 50:
            return content

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Extract and structure key knowledge for an options trading AI agent.\n\n"
                            f"Source: {source}\n\n"
                            f"Content:\n{content[:4000]}\n\n"
                            f"Instructions:\n"
                            f"1. Extract ALL trading-relevant information\n"
                            f"2. Keep strategies, rules, formulas, key levels\n"
                            f"3. Format clearly with bullet points\n"
                            f"4. Write in Hebrew, technical terms in English\n"
                            f"5. Focus on actionable insights"
                        ),
                    }
                ],
            )
            return response.content[0].text.strip()

        except Exception:
            return content[:2000]

    def _generate_topic(self, url: str, content: str) -> str:
        """Generate a descriptive topic name from URL or content."""
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        for line in lines[:5]:
            if 10 < len(line) < 80:
                return line[:50]
        parts = url.rstrip("/").split("/")
        return (parts[-1] or parts[-2] if len(parts) > 1 else url)[:40]

    # ── Knowledge Management ──────────────────────────────────────────────────

    def list_knowledge(self) -> list[dict]:
        """List all learned knowledge topics."""
        if self.memory:
            return self.memory.list_knowledge()
        return []

    def delete_knowledge(self, topic: str) -> bool:
        """Delete specific learned knowledge by topic name."""
        if self.memory and self.memory.knowledge_col is not None:
            try:
                self.memory.knowledge_col.delete_one({"topic": topic})
                return True
            except Exception:
                pass
        return False
