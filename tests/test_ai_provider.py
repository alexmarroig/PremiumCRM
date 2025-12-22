from services.ai.mock_provider import MockAIProvider


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
