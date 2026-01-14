from __future__ import annotations

from typing import Any, Dict, List, Callable

from .provider import AIProvider


SignalFetcher = Callable[[str], Dict[str, Any]]


class IncomeAwareAIProvider(AIProvider):
    def __init__(self, external_signal_fetcher: SignalFetcher | None = None):
        self.external_signal_fetcher = external_signal_fetcher or self._mock_external_signals

    def classify_message(self, message: str, history: List[str] | None = None) -> Dict[str, Any]:
        lowered = message.lower()
        sentiment = "positive" if any(word in lowered for word in ["thanks", "grateful", "appreciate"]) else "neutral"
        if any(word in lowered for word in ["angry", "frustrated", "upset", "bad", "concerned"]):
            sentiment = "irritated"
        urgency = "high" if any(word in lowered for word in ["asap", "urgent", "now", "today"]) else "normal"
        negotiation = any(word in lowered for word in ["price", "discount", "budget", "cost"])
        should_create_task = any(word in lowered for word in ["schedule", "call", "meeting", "invoice", "demo"])

        signals = self.external_signal_fetcher(message)
        income_band = signals.get("income_band", "mid")
        affordability_score = self._calculate_affordability_score(income_band, lowered)
        financial_profile = self._infer_financial_profile(income_band, lowered)

        return {
            "sentiment": sentiment,
            "urgency": urgency,
            "negotiation_signal": negotiation,
            "should_create_task": should_create_task,
            "income_band": income_band,
            "financial_profile": financial_profile,
            "affordability_score": round(affordability_score, 2),
            "signals_used": signals,
        }

    def suggest_reply(self, message: str) -> Dict[str, Any]:
        base_reply = "Thanks for reaching out! I can tailor options to your budget and goals."
        lowered = message.lower()
        if "budget" in lowered or "discount" in lowered:
            base_reply = (
                "Thanks for sharing your budget focus. I can outline a lean option and a premium option so "
                "you can choose the best fit."
            )
        elif "enterprise" in lowered or "annual" in lowered:
            base_reply = (
                "Great to hear about your long-term plans. I'll send a bundled quote with savings for annual terms."
            )

        return {
            "reply": base_reply,
            "confidence": 0.71,
        }

    def suggest_price(self, message: str) -> Dict[str, Any]:
        lowered = message.lower()
        signals = self.external_signal_fetcher(message)
        income_band = signals.get("income_band", "mid")
        profile = self._infer_financial_profile(income_band, lowered)
        affordability_score = self._calculate_affordability_score(income_band, lowered)

        base_min, base_max = 110, 220
        multiplier = {"high": 1.25, "mid": 1.0, "low": 0.8}.get(income_band, 1.0)

        if "discount" in lowered or "budget" in lowered:
            multiplier *= 0.9
        if "enterprise" in lowered or "annual" in lowered:
            multiplier *= 1.1

        min_price = round(base_min * multiplier)
        max_price = round(base_max * multiplier)

        if any(word in lowered for word in ["negotiat", "deal", "price", "discount"]):
            midpoint = (min_price + max_price) / 2
            min_price = round(midpoint * 0.9)
            max_price = round(midpoint * 1.1)

        rationale = [
            f"Income band '{income_band}' suggests a {int(multiplier * 100)}% adjustment",
            "No biometric or location data used",
            "Affordability score considers discounts in the request",
        ]

        return {
            "min_price": min_price,
            "max_price": max_price,
            "confidence": round(min(0.9, 0.55 + affordability_score / 3), 2),
            "financial_profile": profile,
            "income_band": income_band,
            "affordability_score": round(affordability_score, 2),
            "rationale": rationale,
            "questions_to_user": [
                "Do you prefer monthly or annual billing?",
                "Any compliance or onboarding constraints we should factor in?",
            ],
            "signals_used": signals,
        }

    def suggest_followup(self, message: str) -> Dict[str, Any]:
        signals = self.external_signal_fetcher(message)
        followup_actions = ["Send availability for a quick call", "Share pricing tiers overview"]
        if signals.get("income_band") == "low":
            followup_actions.append("Offer starter bundle with limited seats")
        elif signals.get("income_band") == "high":
            followup_actions.append("Propose premium onboarding package")

        return {
            "actions": followup_actions,
            "timing": "within 1 day" if "urgent" in message.lower() else "within 2 days",
        }

    def _mock_external_signals(self, message: str) -> Dict[str, Any]:
        lowered = message.lower()
        if any(keyword in lowered for keyword in ["enterprise", "funded", "investment", "venture"]):
            band = "high"
        elif any(keyword in lowered for keyword in ["student", "budget", "nonprofit", "grant"]):
            band = "low"
        else:
            band = "mid"

        return {
            "income_band": band,
            "signals": ["credit_model_v1", "public_company_size"] if band == "high" else ["credit_model_v1"],
            "consent_required": True,
        }

    def _calculate_affordability_score(self, income_band: str, lowered_message: str) -> float:
        base_scores = {"high": 0.82, "mid": 0.58, "low": 0.35}
        score = base_scores.get(income_band, 0.58)
        if "discount" in lowered_message or "budget" in lowered_message:
            score -= 0.08
        if "premium" in lowered_message or "enterprise" in lowered_message:
            score += 0.05
        return max(0.1, min(0.95, score))

    def _infer_financial_profile(self, income_band: str, lowered_message: str) -> str:
        if income_band == "high" and "budget" not in lowered_message:
            return "expansive"
        if income_band == "low" or "discount" in lowered_message:
            return "budget_sensitive"
        if "scale" in lowered_message or "growth" in lowered_message:
            return "steady_growth"
        return "balanced"
