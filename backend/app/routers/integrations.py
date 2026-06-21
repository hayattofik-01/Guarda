from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.config import settings
from app.models import User
from app.services.cala import CalaClient


class IntegrationStatus(BaseModel):
    supabase: bool
    resend: bool
    cala: bool
    shodan: bool
    censys: bool
    securitytrails: bool
    virustotal: bool
    nvd: bool
    slack: bool


router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatus)
def status(user: User = Depends(get_current_user)) -> IntegrationStatus:
    return IntegrationStatus(
        supabase=bool(settings.supabase_db_url),
        resend=bool(settings.resend_api_key),
        cala=bool(settings.cala_api_key),
        shodan=bool(settings.shodan_api_key),
        censys=bool(settings.censys_api_id and settings.censys_api_secret),
        securitytrails=bool(settings.securitytrails_api_key),
        virustotal=bool(settings.virustotal_api_key),
        nvd=bool(settings.nvd_api_key),
        slack=bool(settings.slack_webhook_url),
    )


@router.get("/cala/health")
def cala_health(user: User = Depends(get_current_user)) -> dict:
    return CalaClient().health()
