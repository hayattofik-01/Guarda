import pytest

from app.config import settings
from app.services import cala_intel, gdpr


@pytest.fixture(autouse=True)
def _isolate_cala(monkeypatch):
    """Keep tests hermetic: no live Cala calls, no cross-test cache bleed."""
    monkeypatch.setattr(settings, "cala_api_key", "", raising=False)
    gdpr._CACHE.clear()
    cala_intel._CACHE.clear()
    yield
    gdpr._CACHE.clear()
    cala_intel._CACHE.clear()
