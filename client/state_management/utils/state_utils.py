"""
Утилиты для управления состояниями
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..core.types import AppState, StateInfo, StateMetrics

logger = logging.getLogger(__name__)


def format_duration(seconds: float) -> str:
    """
    Форматирует длительность в читаемый вид
    
    Args:
        seconds: Секунды
        
    Returns:
        str: Отформатированная строка
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_state_info(state_info: StateInfo) -> str:
    """
    Форматирует информацию о состоянии
    
    Args:
        state_info: Информация о состоянии
        
    Returns:
        str: Отформатированная строка
    """
    duration_str = format_duration(state_info.duration)
    timestamp_str = state_info.timestamp.strftime("%H:%M:%S")
    
    return f"[{timestamp_str}] {state_info.state.value} ({duration_str}) - {state_info.reason}"


def format_metrics(metrics: StateMetrics) -> str:
    """
    Форматирует метрики в читаемый вид
    
    Args:
        metrics: Метрики
        
    Returns:
        str: Отформатированная строка
    """
    success_rate = (metrics.successful_transitions / metrics.total_transitions * 100) if metrics.total_transitions > 0 else 0
    
    return f"""
Метрики состояний:
  Всего переходов: {metrics.total_transitions}
  Успешных: {metrics.successful_transitions}
  Неудачных: {metrics.failed_transitions}
  Успешность: {success_rate:.1f}%
  
  Время в состояниях:
    Сон: {format_duration(metrics.time_in_sleeping)}
    Прослушивание: {format_duration(metrics.time_in_listening)}
    Обработка: {format_duration(metrics.time_in_processing)}
    Ошибка: {format_duration(metrics.time_in_error)}
  
  Среднее время перехода: {format_duration(metrics.average_transition_time)}
  Ошибок: {metrics.error_count}
  Восстановлений: {metrics.recovery_count}
"""


def get_state_summary(state_history: List[StateInfo], limit: int = 10) -> str:
    """
    Получает сводку по состояниям
    
    Args:
        state_history: История состояний
        limit: Максимальное количество записей
        
    Returns:
        str: Сводка
    """
    if not state_history:
        return "История состояний пуста"
    
    recent_states = state_history[-limit:] if limit > 0 else state_history
    
    summary = "Последние состояния:\n"
    for state_info in recent_states:
        summary += f"  {format_state_info(state_info)}\n"
    
    return summary


def calculate_state_statistics(state_history: List[StateInfo]) -> Dict[str, Any]:
    """
    Вычисляет статистику по состояниям
    
    Args:
        state_history: История состояний
        
    Returns:
        Dict[str, Any]: Статистика
    """
    if not state_history:
        return {}
    
    # Группируем по состояниям
    state_counts = {}
    state_durations = {}
    
    for state_info in state_history:
        state_name = state_info.state.value
        
        if state_name not in state_counts:
            state_counts[state_name] = 0
            state_durations[state_name] = 0.0
        
        state_counts[state_name] += 1
        state_durations[state_name] += state_info.duration
    
    # Вычисляем средние значения
    state_averages = {}
    for state_name, total_duration in state_durations.items():
        count = state_counts[state_name]
        state_averages[state_name] = total_duration / count if count > 0 else 0.0
    
    return {
        'state_counts': state_counts,
        'state_durations': state_durations,
        'state_averages': state_averages,
        'total_states': len(state_history),
        'unique_states': len(state_counts)
    }


def find_state_patterns(state_history: List[StateInfo], pattern_length: int = 3) -> List[List[AppState]]:
    """
    Находит повторяющиеся паттерны состояний
    
    Args:
        state_history: История состояний
        pattern_length: Длина паттерна
        
    Returns:
        List[List[AppState]]: Список паттернов
    """
    if len(state_history) < pattern_length:
        return []
    
    patterns = []
    for i in range(len(state_history) - pattern_length + 1):
        pattern = [state_info.state for state_info in state_history[i:i + pattern_length]]
        patterns.append(pattern)
    
    return patterns


def detect_anomalies(state_history: List[StateInfo], threshold: float = 2.0) -> List[StateInfo]:
    """
    Обнаруживает аномалии в истории состояний
    
    Args:
        state_history: История состояний
        threshold: Порог для обнаружения аномалий
        
    Returns:
        List[StateInfo]: Список аномальных состояний
    """
    if len(state_history) < 3:
        return []
    
    anomalies = []
    durations = [state_info.duration for state_info in state_history]
    
    # Вычисляем среднее и стандартное отклонение
    mean_duration = sum(durations) / len(durations)
    variance = sum((d - mean_duration) ** 2 for d in durations) / len(durations)
    std_deviation = variance ** 0.5
    
    # Находим аномалии
    for state_info in state_history:
        if abs(state_info.duration - mean_duration) > threshold * std_deviation:
            anomalies.append(state_info)
    
    return anomalies


def export_state_data(state_history: List[StateInfo], metrics: StateMetrics) -> Dict[str, Any]:
    """
    Экспортирует данные состояний в словарь
    
    Args:
        state_history: История состояний
        metrics: Метрики
        
    Returns:
        Dict[str, Any]: Экспортированные данные
    """
    return {
        'export_time': datetime.now().isoformat(),
        'state_history': [
            {
                'state': state_info.state.value,
                'timestamp': state_info.timestamp.isoformat(),
                'duration': state_info.duration,
                'reason': state_info.reason,
                'metadata': state_info.metadata or {}
            }
            for state_info in state_history
        ],
        'metrics': {
            'total_transitions': metrics.total_transitions,
            'successful_transitions': metrics.successful_transitions,
            'failed_transitions': metrics.failed_transitions,
            'time_in_sleeping': metrics.time_in_sleeping,
            'time_in_listening': metrics.time_in_listening,
            'time_in_processing': metrics.time_in_processing,
            'time_in_error': metrics.time_in_error,
            'average_transition_time': metrics.average_transition_time,
            'error_count': metrics.error_count,
            'recovery_count': metrics.recovery_count,
            'last_transition_time': metrics.last_transition_time.isoformat() if metrics.last_transition_time else None
        },
        'statistics': calculate_state_statistics(state_history)
    }
