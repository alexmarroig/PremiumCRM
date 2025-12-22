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
