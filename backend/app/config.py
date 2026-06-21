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
    subfinder_max_time: int = 60 * 5
    # nuclei is the heaviest step; bound it so onboarding scans stay snappy on
    # small (free-tier) instances. Caps targets and enforces an overall deadline
    # (partial results are kept if the deadline is hit).
    nuclei_max_targets: int = 15
    nuclei_deadline_seconds: int = 90
    nuclei_concurrency: int = 25
    nuclei_rate_limit: int = 150
    nuclei_request_timeout: int = 5

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
