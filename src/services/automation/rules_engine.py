from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple


def compile_rule(natural_language: str) -> dict:
    # Simple stub compiler
    keywords = natural_language.lower().split()
    return {"keywords": keywords, "created_at": datetime.utcnow().isoformat()}


def evaluate_rule(compiled: dict, message_text: str) -> bool:
    if not compiled:
        return False
    keywords: List[str] = compiled.get("keywords", [])
    return any(k in message_text.lower() for k in keywords)


def validate_flow_schema(compiled_json: dict) -> Tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(compiled_json, dict):
        errors.append("Flow must be a dict")
    elif "nodes" not in compiled_json:
        errors.append("Missing nodes array")
    return (len(errors) == 0, errors)


def simulate_flow(compiled_json: dict, context: dict) -> dict:
    nodes = compiled_json.get("nodes", []) if isinstance(compiled_json, dict) else []
    matched_nodes = [n for n in nodes if context.get("intent") in n.get("intents", [])] if nodes else []
    suggested_actions = []
    for node in matched_nodes:
        suggested_actions.extend(node.get("actions", []))
    return {"matched_nodes": matched_nodes, "suggested_actions": suggested_actions}
