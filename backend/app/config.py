from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "Guarda"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"

    # Infra. Prefer Supabase when SUPABASE_DB_URL is set, else fall back to DATABASE_URL.
    database_url: str = "postgresql+psycopg://guarda:guarda@db:5432/guarda"
    supabase_db_url: str = ""
    redis_url: str = "redis://redis:6379/0"

    @property
    def resolved_database_url(self) -> str:
        raw = self.supabase_db_url or self.database_url
        # Normalize to the psycopg v3 driver SQLAlchemy expects.
        if raw.startswith("postgresql+psycopg://"):
            url = raw
        elif raw.startswith("postgresql://"):
            url = raw.replace("postgresql://", "postgresql+psycopg://", 1)
        elif raw.startswith("postgres://"):
            url = raw.replace("postgres://", "postgresql+psycopg://", 1)
        else:
            url = raw
        # Supabase requires TLS; add sslmode=require if connecting to supabase.
        if "supabase." in url and "sslmode=" not in url:
            url += ("&" if "?" in url else "?") + "sslmode=require"
        return url

    # Scanner tuning
    nuclei_tags: str = "exposure,exposures,misconfig,config,backup,logs,secret,token"
    nuclei_severity: str = "low,medium,high,critical"
    scan_timeout_seconds: int = 60 * 30
    # A scan stuck in "running"/"queued" longer than this (e.g. the in-process
    # task was OOM-killed on a small free-tier box) is reclaimed and marked
    # failed so the UI never spins forever.
    scan_stuck_after_seconds: int = 60 * 6
    # Document checks are fast; one still queued/running this long was lost to a
    # restart/sleep and is reclaimed so the UI never shows "Queued" forever.
    document_stuck_after_seconds: int = 120
    # subfinder streams subdomain strings (trivial memory) so it's safe to query
    # all passive sources for rich, consistent discovery; the memory guard is the
    # httpx host cap below, not the breadth of subdomain enumeration.
    subfinder_max_time: int = 120
    subfinder_use_all_sources: bool = True
    # nuclei is the heaviest step; bound it so onboarding scans stay snappy on
    # small (free-tier) instances. Caps targets and enforces an overall deadline
    # (partial results are kept if the deadline is hit).
    nuclei_max_targets: int = 10
    nuclei_deadline_seconds: int = 45
    nuclei_concurrency: int = 8
    nuclei_rate_limit: int = 80
    nuclei_request_timeout: int = 5
    # theHarvester and httpx can stall on slow public sources / large host lists
    # and spike memory; bound each tightly so an in-process scan finishes quickly
    # without OOM-killing the box (partial output is kept).
    harvester_deadline_seconds: int = 45
    httpx_deadline_seconds: int = 45
    # Cap how many discovered hosts httpx probes and its thread count. Probing
    # hundreds of hosts with tech-detect is the main memory spike that OOM-kills
    # a 512MB instance; all subdomains are still reported as footprint findings.
    httpx_max_hosts: int = 60
    httpx_threads: int = 12

    # Devin API (powers the AI remediation "advice" agent; optional)
    devin_api_key: str = ""
    devin_api_base: str = "https://api.devin.ai/v1"

    # Shared secret protecting the scheduler endpoint (/api/cron/tick).
    cron_secret: str = ""

    # Integrations (all optional)
    cala_api_key: str = ""
    cala_mcp_url: str = "https://api.cala.ai/mcp/"
    nvd_api_key: str = ""
    vulners_api_key: str = ""
    shodan_api_key: str = ""
    censys_api_id: str = ""
    censys_api_secret: str = ""
    securitytrails_api_key: str = ""
    virustotal_api_key: str = ""
    sendgrid_api_key: str = ""
    slack_webhook_url: str = ""
    # Resend (primary email provider)
    resend_api_key: str = ""
    resend_from_email: str = "Guarda <onboarding@resend.dev>"
    # Twilio WhatsApp (optional) — used to send alerts to the user's WhatsApp.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox number
    # public base URL used in report links inside emails
    public_app_url: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
