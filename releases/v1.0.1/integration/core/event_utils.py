"""Утилиты для работы с событиями EventBus (dict-формат)."""
from typing import Any, Dict


def event_type(event: Any, default: str = "unknown") -> str:
    """Безопасно получить тип события как строку."""
    if isinstance(event, dict):
        return event.get("type", default)
    return getattr(event, "event_type", default)


def event_data(event: Any) -> Dict[str, Any]:
    """Безопасно получить data из события."""
    if isinstance(event, dict):
        return event.get("data", {}) or {}
    return getattr(event, "data", {}) or {}

