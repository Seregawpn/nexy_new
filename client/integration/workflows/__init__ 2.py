"""
Workflows - Координаторы режимов приложения

Этот пакет содержит workflow'ы для управления сложными цепочками действий
в разных режимах приложения. Workflow'ы НЕ дублируют функционал интеграций,
а координируют их взаимодействие через EventBus.

Архитектурные принципы:
- Событийная архитектура - все через EventBus
- Тонкие координаторы - не дублируют логику модулей
- Умные таймауты - ждут реальных событий, не слепых таймеров
- Graceful обработка ошибок и прерываний
- macOS совместимость - без нарушения системных ограничений
"""

from .base_workflow import BaseWorkflow, WorkflowState
from .listening_workflow import ListeningWorkflow
from .processing_workflow import ProcessingWorkflow, ProcessingStage

__all__ = [
    'BaseWorkflow',
    'WorkflowState', 
    'ListeningWorkflow',
    'ProcessingWorkflow',
    'ProcessingStage'
]

__version__ = '1.0.0'
__author__ = 'Nexy Team'
