from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIProvider(ABC):
    @abstractmethod
    def classify_message(self, message: str, history: List[str] | None = None) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def suggest_reply(self, message: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def suggest_price(self, message: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def suggest_followup(self, message: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def summarize_conversation(self, messages: List[str]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def create_flow_from_prompt(self, prompt: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def transcribe_audio(self, audio_base64: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def synthesize_speech(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError
