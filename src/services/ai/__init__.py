from functools import lru_cache

from core.config import get_settings
from .income_provider import IncomeAwareAIProvider
from .mock_provider import MockAIProvider
from .provider import AIProvider


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    backend = settings.ai_provider_backend.lower()
    if backend == "income":
        return IncomeAwareAIProvider()
    return MockAIProvider()


__all__ = [
    "AIProvider",
    "MockAIProvider",
    "IncomeAwareAIProvider",
    "get_ai_provider",
]
