FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NUCLEI_VERSION=3.3.7

# Scanner system deps: nmap (ports/services) + nuclei (templated checks).
RUN apt-get update \
    && apt-get install -y --no-install-recommends nmap ca-certificates curl unzip \
    && rm -rf /var/lib/apt/lists/*

RUN arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
         amd64) NARCH=amd64 ;; \
         arm64) NARCH=arm64 ;; \
         *) NARCH=amd64 ;; \
       esac \
    && curl -sSL -o /tmp/nuclei.zip \
       "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_${NARCH}.zip" \
    && unzip -o /tmp/nuclei.zip -d /usr/local/bin nuclei \
    && rm /tmp/nuclei.zip \
    && nuclei -version || true

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY . .

# Pre-fetch nuclei templates (best effort; ignored if offline at build time).
RUN nuclei -update-templates -disable-update-check 2>/dev/null || true

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
