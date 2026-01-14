from services.ai import get_ai_provider
from services.ai.income_provider import IncomeAwareAIProvider
from services.ai.mock_provider import MockAIProvider


def teardown_function() -> None:
    # Clear cached provider between tests to allow env overrides
    get_ai_provider.cache_clear()


def test_mock_provider_classification_detects_urgency():
    provider = MockAIProvider()
    result = provider.classify_message("Please respond ASAP about price")
    assert result["urgency"] == "high"
    assert result["negotiation_signal"] is True


def test_mock_provider_price_range():
    provider = MockAIProvider()
    result = provider.suggest_price("What's the budget?")
    assert result["min_price"] < result["max_price"]
    assert "questions_to_user" in result


def test_income_provider_low_band_profiles_budget_focus():
    provider = IncomeAwareAIProvider()
    message = "Student budget is limited and looking for a discount"
    result = provider.classify_message(message)
    assert result["income_band"] == "low"
    assert result["financial_profile"] == "budget_sensitive"
    assert result["affordability_score"] < 0.4

    pricing = provider.suggest_price(message)
    assert pricing["income_band"] == "low"
    assert pricing["max_price"] < 200
    assert pricing["min_price"] < pricing["max_price"]


def test_income_provider_high_band_prefers_premium_ranges():
    provider = IncomeAwareAIProvider()
    message = "Enterprise team planning annual contract, not worried about price"
    result = provider.classify_message(message)
    assert result["income_band"] == "high"
    assert result["financial_profile"] == "expansive"
    assert result["affordability_score"] > 0.8

    pricing = provider.suggest_price(message)
    assert pricing["min_price"] > 120
    assert pricing["max_price"] > 240
    assert pricing["financial_profile"] == "expansive"


def test_get_ai_provider_uses_env_backend(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_BACKEND", "income")
    provider = get_ai_provider()
    assert isinstance(provider, IncomeAwareAIProvider)

    monkeypatch.setenv("AI_PROVIDER_BACKEND", "mock")
    get_ai_provider.cache_clear()
    provider = get_ai_provider()
    assert isinstance(provider, MockAIProvider)
