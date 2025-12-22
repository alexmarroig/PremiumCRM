from typing import Any, Dict, List
import random

from .provider import AIProvider


class MockAIProvider(AIProvider):
    def classify_message(self, message: str, history: List[str] | None = None) -> Dict[str, Any]:
        lowered = message.lower()
        sentiment = "positive" if "thank" in lowered or ":)" in lowered else "neutral"
        if any(word in lowered for word in ["angry", "frustrated", "upset", "bad"]):
            sentiment = "irritated"
        urgency = "high" if any(word in lowered for word in ["asap", "urgent", "now", "today"]) else "normal"
        negotiation = any(word in lowered for word in ["price", "discount", "budget", "cost"])
        should_create_task = any(word in lowered for word in ["schedule", "call", "meeting", "invoice"])
        return {
            "sentiment": sentiment,
            "urgency": urgency,
            "negotiation_signal": negotiation,
            "should_create_task": should_create_task,
        }

    def suggest_reply(self, message: str) -> Dict[str, Any]:
        return {
            "reply": "Thanks for reaching out! Can you share a bit more so I can help?",
            "confidence": 0.62,
        }

    def suggest_price(self, message: str) -> Dict[str, Any]:
        base_min, base_max = 100, 200
        if "budget" in message.lower():
            base_min, base_max = 80, 150
        return {
            "min_price": base_min,
            "max_price": base_max,
            "confidence": 0.55,
            "rationale": ["Based on similar negotiations", "No visual data used"],
            "questions_to_user": ["Any existing discounts?", "Target close date?"],
        }

    def suggest_followup(self, message: str) -> Dict[str, Any]:
        return {
            "actions": [
                "Send availability for a quick call",
                "Share one-pager about offering",
            ],
            "timing": "within 1 day",
        }
