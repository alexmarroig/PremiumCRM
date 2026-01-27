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
            "reply": "Obrigado pelo contato! Pode compartilhar mais detalhes para eu ajudar?",
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
            "rationale": ["Baseado em negociações similares", "Nenhum dado visual foi usado"],
            "questions_to_user": ["Há descontos existentes?", "Qual a data alvo de fechamento?"],
        }

    def suggest_followup(self, message: str) -> Dict[str, Any]:
        return {
            "actions": [
                "Enviar horários para uma conversa rápida",
                "Compartilhar um resumo da oferta",
            ],
            "timing": "em até 1 dia",
        }

    def summarize_conversation(self, messages: List[str]) -> Dict[str, Any]:
        summary = "Resumo automático indisponível."
        if messages:
            summary = f"Conversa ativa com lead. Última mensagem: \"{messages[-1][:120]}\"."
        return {
            "summary": summary,
            "suggestions": [
                "Responder com confirmação dos próximos passos.",
                "Enviar proposta rápida.",
                "Perguntar sobre prazo e orçamento.",
            ],
        }

    def create_flow_from_prompt(self, prompt: str) -> Dict[str, Any]:
        return {
            "name": "Fluxo Alfred",
            "description": f"Fluxo criado a partir do prompt: {prompt[:140]}",
            "compiled_json": {
                "trigger": "lead_message",
                "condition": prompt,
                "response": "Vamos conversar sobre sua necessidade. Posso enviar opções?",
            },
        }

    def transcribe_audio(self, audio_base64: str) -> Dict[str, Any]:
        return {
            "transcription": "Transcrição simulada do áudio.",
            "language": "pt-BR",
            "confidence": 0.4,
        }

    def synthesize_speech(self, text: str) -> Dict[str, Any]:
        return {
            "audio_base64": "",
            "voice": "pt-BR-standard",
            "message": "Áudio sintetizado (simulado).",
        }
