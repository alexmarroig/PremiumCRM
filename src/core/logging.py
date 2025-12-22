import logging
import sys
from typing import Any, Dict

from pythonjsonlogger import jsonlogger


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_extra(user_id: str | None = None, **kwargs: Any) -> Dict[str, Any]:
    data = {"user_id": user_id}
    data.update(kwargs)
    return {"extra": data}
