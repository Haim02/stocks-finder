# ──────────────────────────────────────────────────────────────────────────────
# Autonomous Trading Agent — Production Dockerfile
#
# Base  : python:3.13-slim (Debian Bookworm, amd64)
# User  : non-root 'agent' (UID 1000) for Railway/VPS security
# Chrome: installed from Google's official APT repo (stable, auto-updates)
# Driver: webdriver-manager downloads ChromeDriver at first run, cached in
#         /app/drivers/ (WDM_LOCAL=1) — survives image rebuilds via a volume
#
# Build:
#   docker build -t trading-agent .
#
# Run (Railway sets CMD automatically from Dockerfile):
#   python run_agent.py          # daemon: scheduler 16:45 IL + Telegram bot
#   python run_agent.py --once   # single options-agent run and exit
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim

# ── Timezone (Israel) — set before any apt install ────────────────────────────
ENV TZ=Asia/Jerusalem
ENV DEBIAN_FRONTEND=noninteractive

# ── System packages in ONE layer ──────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essentials
    wget gnupg ca-certificates tzdata gcc \
    # Chrome shared libraries (headless — no audio, no GPU, no Wayland)
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

# ── Google Chrome — official APT repository ───────────────────────────────────
RUN wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
        https://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ── Python environment ────────────────────────────────────────────────────────
WORKDIR /app

# Install deps before copying code — layer is cached until requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY . .

# ── Runtime environment variables ────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Chrome flags for containers
ENV CHROME_HEADLESS=1
# Suppress webdriver-manager download noise
ENV WDM_LOG=0
# Cache ChromeDriver inside the project dir so non-root user can write to it
ENV WDM_LOCAL=1

# ── Non-root user (required by Railway and security best practice) ─────────────
RUN useradd -m -u 1000 agent \
    && mkdir -p /app/drivers /app/chrome_profile \
    && chown -R agent:agent /app
USER agent

# ── Start daemon: scheduler (16:45 Israel) + Telegram bot ────────────────────
CMD ["python", "run_agent.py"]
