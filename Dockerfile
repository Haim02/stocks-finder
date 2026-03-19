# ──────────────────────────────────────────────────────────────────────────────
# Autonomous Trading Agent — Dockerfile
#
# Includes:
#   - Python 3.13 slim (Debian Bookworm)
#   - Correct Israel timezone (Asia/Jerusalem)
#   - Google Chrome via official APT repo (stable, not fragile .deb download)
#   - Selenium + webdriver-manager (auto-matches ChromeDriver to Chrome)
#   - python-telegram-bot, APScheduler, all scraping libs
#
# Build:   docker build -t trading-agent .
# One-off: docker run --env-file .env trading-agent python run_agent.py
# Daemon:  docker compose up -d
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim

# ── Timezone — must be set before tzdata installs ────────────────────────────
ENV TZ=Asia/Jerusalem
ENV DEBIAN_FRONTEND=noninteractive

# ── System packages (single layer for smaller image) ─────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core tools
    wget gnupg ca-certificates tzdata gcc \
    # Chrome runtime shared libraries (headless — no audio/GPU)
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# ── Google Chrome via official APT repository (more stable than direct .deb) ─
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
        https://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────────────
WORKDIR /app

# Copy requirements first so this layer is cached unless requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        "python-telegram-bot>=21.0" \
        "apscheduler>=3.10" \
        "selenium>=4.15" \
        "webdriver-manager>=4.0"

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Runtime environment ───────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
# Tell Chrome to run headless (read by tradingview_service.py)
ENV CHROME_HEADLESS=1
# Suppress verbose webdriver-manager download logs
ENV WDM_LOG=0
# Use a project-local driver cache so the non-root user can write to it
ENV WDM_LOCAL=1

# ── Non-root user (security best practice) ────────────────────────────────────
# Create user BEFORE chown — single layer
RUN useradd -m -u 1000 agent \
    && chown -R agent:agent /app
USER agent

# ── Default: daemon mode (scheduler 16:45 Israel + Telegram bot) ─────────────
CMD ["python", "run_agent.py", "--daemon"]
