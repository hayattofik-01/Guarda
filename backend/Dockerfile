FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NUCLEI_VERSION=3.3.7 \
    SUBFINDER_VERSION=2.6.6 \
    HTTPX_VERSION=1.6.9 \
    GITLEAKS_VERSION=8.21.2

# System deps: git (gitleaks clones), plus fetch helpers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl unzip tar \
    && rm -rf /var/lib/apt/lists/*

# Free OSINT recon binaries (ProjectDiscovery + gitleaks).
RUN arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
         amd64) NARCH=amd64; GARCH=x64 ;; \
         arm64) NARCH=arm64; GARCH=arm64 ;; \
         *) NARCH=amd64; GARCH=x64 ;; \
       esac \
    && curl -sSL -o /tmp/nuclei.zip \
       "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_${NARCH}.zip" \
    && unzip -o /tmp/nuclei.zip -d /usr/local/bin nuclei \
    && curl -sSL -o /tmp/subfinder.zip \
       "https://github.com/projectdiscovery/subfinder/releases/download/v${SUBFINDER_VERSION}/subfinder_${SUBFINDER_VERSION}_linux_${NARCH}.zip" \
    && unzip -o /tmp/subfinder.zip -d /usr/local/bin subfinder \
    && curl -sSL -o /tmp/httpx.zip \
       "https://github.com/projectdiscovery/httpx/releases/download/v${HTTPX_VERSION}/httpx_${HTTPX_VERSION}_linux_${NARCH}.zip" \
    && unzip -o /tmp/httpx.zip -d /usr/local/bin httpx \
    && curl -sSL -o /tmp/gitleaks.tar.gz \
       "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${GARCH}.tar.gz" \
    && tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks \
    && rm -f /tmp/nuclei.zip /tmp/subfinder.zip /tmp/httpx.zip /tmp/gitleaks.tar.gz \
    && chmod +x /usr/local/bin/nuclei /usr/local/bin/subfinder /usr/local/bin/httpx /usr/local/bin/gitleaks \
    && nuclei -version || true

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

# theHarvester (passive email/host OSINT). Best-effort: build proceeds if it fails.
RUN pip install --no-cache-dir theHarvester || echo "theHarvester install skipped"

COPY . .

# Pre-fetch nuclei templates (best effort; ignored if offline at build time).
RUN nuclei -update-templates -disable-update-check 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
