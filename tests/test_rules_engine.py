from services.automation.rules_engine import compile_rule, evaluate_rule, simulate_flow, validate_flow_schema


def test_compile_and_evaluate_rule():
    compiled = compile_rule("notify when angry client")
    assert "keywords" in compiled
    assert evaluate_rule(compiled, "customer is angry about pricing")


def test_validate_flow_schema():
    valid, errors = validate_flow_schema({"nodes": []})
    assert valid
    assert errors == []


def test_simulate_flow_matches_actions():
    compiled = {"nodes": [{"intents": ["pricing"], "actions": ["send quote"]}]}
    result = simulate_flow(compiled, {"intent": "pricing"})
    assert result["suggested_actions"] == ["send quote"]
