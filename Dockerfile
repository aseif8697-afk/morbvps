FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 BASE_PATH=/data DEBIAN_FRONTEND=noninteractive
WORKDIR /app
# Runtime image for the panel and user applications: Python, Node.js, PHP CLI,
# Composer and common PHP extensions. The checks below fail the build instead
# of allowing a deployed container where `php` silently does not exist.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git unzip zip \
    nodejs npm \
    php-cli php-curl php-mbstring php-xml php-zip \
    composer \
    && command -v python3 \
    && command -v node \
    && command -v npm \
    && command -v php \
    && command -v composer \
    && php -v \
    && node --version \
    && composer --version \
    && python3 -m venv /tmp/ms-vps-venv \
    && /tmp/ms-vps-venv/bin/python -c 'print("Python venv OK")' \
    && node -e 'console.log("Node.js runtime OK")' \
    && php -r 'echo "PHP CLI runtime OK\\n";' \
    && rm -rf /tmp/ms-vps-venv \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY panel.py ./panel.py
COPY sandbox_runner.py ./sandbox_runner.py
COPY isolation.py ./isolation.py
EXPOSE 8080
CMD ["python", "panel.py"]
