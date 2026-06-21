from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "Perimeter"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"

    # Infra
    database_url: str = "postgresql+psycopg://perimeter:perimeter@db:5432/perimeter"
    redis_url: str = "redis://redis:6379/0"

    # Scanner tuning
    nmap_default_args: str = "-Pn -T4 --top-ports 1000 -sV"
    nuclei_severity: str = "low,medium,high,critical"
    scan_timeout_seconds: int = 60 * 30

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
    sendgrid_from_email: str = "alerts@perimeter.local"
    slack_webhook_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
