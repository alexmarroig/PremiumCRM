from collections import defaultdict
from typing import Callable, Dict, List, Any


class EventBus:
    def __init__(self) -> None:
        self.subscribers: Dict[str, List[Callable[[dict], None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[[dict], None]) -> None:
        self.subscribers[event].append(handler)

    def publish(self, event: str, payload: dict) -> None:
        for handler in self.subscribers.get(event, []):
            handler(payload)


event_bus = EventBus()
