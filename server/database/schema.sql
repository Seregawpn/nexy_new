-- =====================================================
-- СХЕМА БАЗЫ ДАННЫХ ДЛЯ ГОЛОСОВОГО АССИСТЕНТА
-- PostgreSQL 15+ с JSONB полями для максимальной гибкости
-- =====================================================

-- Включаем расширение для UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hardware_id_hash VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Гибкие метаданные пользователя
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Индексы для быстрого поиска
    CONSTRAINT users_hardware_id_hash_not_empty CHECK (hardware_id_hash != '')
);

-- Индекс для JSONB метаданных
CREATE INDEX idx_users_metadata ON users USING GIN (metadata);

-- =====================================================
-- ТАБЛИЦА СЕССИЙ
-- =====================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    
    -- Гибкие метаданные сессии
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Статус сессии
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'ended', 'timeout')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для сессий
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_start_time ON sessions(start_time);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_metadata ON sessions USING GIN (metadata);

-- =====================================================
-- ТАБЛИЦА КОМАНД ПОЛЬЗОВАТЕЛЕЙ
-- =====================================================
CREATE TABLE commands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Основная информация о команде
    prompt TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    
    -- Гибкие метаданные команды
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для команд
CREATE INDEX idx_commands_session_id ON commands(session_id);
CREATE INDEX idx_commands_language ON commands(language);
CREATE INDEX idx_commands_created_at ON commands(created_at);
CREATE INDEX idx_commands_metadata ON commands USING GIN (metadata);

-- =====================================================
-- ТАБЛИЦА ОТВЕТОВ LLM
-- =====================================================
CREATE TABLE llm_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    command_id UUID NOT NULL REFERENCES commands(id) ON DELETE CASCADE,
    
    -- Основная информация об ответе
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    
    -- Информация о модели LLM
    model_info JSONB DEFAULT '{}'::jsonb,
    
    -- Метрики производительности
    performance_metrics JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для ответов LLM
CREATE INDEX idx_llm_answers_command_id ON llm_answers(command_id);
CREATE INDEX idx_llm_answers_model_info ON llm_answers USING GIN (model_info);
CREATE INDEX idx_llm_answers_performance_metrics ON llm_answers USING GIN (performance_metrics);

-- =====================================================
-- ТАБЛИЦА СКРИНШОТОВ (МЕТАДАННЫЕ)
-- =====================================================
CREATE TABLE screenshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Путь к файлу в облачном хранилище
    file_path VARCHAR(500),
    file_url VARCHAR(1000),
    
    -- Метаданные скриншота
    metadata JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для скриншотов
CREATE INDEX idx_screenshots_session_id ON screenshots(session_id);
CREATE INDEX idx_screenshots_metadata ON screenshots USING GIN (metadata);

-- =====================================================
-- ТАБЛИЦА МЕТРИК ПРОИЗВОДИТЕЛЬНОСТИ
-- =====================================================
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Тип метрики
    metric_type VARCHAR(50) NOT NULL,
    
    -- Значение метрики (гибкое JSONB)
    metric_value JSONB NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для метрик
CREATE INDEX idx_performance_metrics_session_id ON performance_metrics(session_id);
CREATE INDEX idx_performance_metrics_type ON performance_metrics(metric_type);
CREATE INDEX idx_performance_metrics_value ON performance_metrics USING GIN (metric_value);

-- =====================================================
-- ТРИГГЕРЫ ДЛЯ ОБНОВЛЕНИЯ TIMESTAMP
-- =====================================================

-- Функция для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггеры для обновления updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ПРИМЕРЫ JSONB СТРУКТУР
-- =====================================================

-- Пример metadata для пользователя
/*
{
  "hardware_info": {
    "mac_address": "00:11:22:33:44:55",
    "serial_number": "C02ABC123DEF",
    "volume_uuid": "12345678-1234-1234-1234-123456789abc"
  },
  "system_info": {
    "os_version": "macOS 14.0",
    "python_version": "3.12.7",
    "app_version": "1.0.0"
  },
  "preferences": {
    "language": "ru",
    "voice_speed": 1.0,
    "auto_capture_screenshots": true
  }
}
*/

-- Пример metadata для команды
/*
{
  "input_method": "voice",
  "duration_ms": 2500,
  "confidence": 0.95,
  "noise_level": "low",
  "device_info": {
    "microphone": "built-in",
    "sample_rate": 44100,
    "channels": 1
  },
  "stt_engine": "google_speech",
  "language_detected": "ru"
}
*/

-- Пример model_info для ответа LLM
/*
{
  "model_name": "gemini-2.0-flash-exp",
  "model_version": "1.0",
  "provider": "google",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9
  },
  "features": ["multimodal", "streaming"]
}
*/

-- Пример performance_metrics для ответа LLM
/*
{
  "response_time_ms": 1200,
  "tokens_generated": 150,
  "tokens_per_second": 125.0,
  "screenshot_used": true,
  "screenshot_size_bytes": 250000,
  "processing_stages": {
    "image_analysis_ms": 300,
    "text_generation_ms": 900
  }
}
*/

-- Пример metadata для скриншота
/*
{
  "dimensions": {
    "width": 1440,
    "height": 900
  },
  "format": "webp",
  "compression": {
    "quality": 80,
    "size_bytes": 250000,
    "compression_ratio": 0.15
  },
  "capture_method": "automatic",
  "window_info": {
    "active_app": "Safari",
    "window_title": "Google - Safari"
  }
}
*/

-- =====================================================
-- СТАТИСТИЧЕСКИЕ ЗАПРОСЫ
-- =====================================================

-- Количество команд по языкам
/*
SELECT 
    language,
    COUNT(*) as command_count,
    AVG(LENGTH(prompt)) as avg_prompt_length
FROM commands 
GROUP BY language 
ORDER BY command_count DESC;
*/

-- Время ответа LLM по моделям
/*
SELECT 
    model_info->>'model_name' as model_name,
    AVG((performance_metrics->>'response_time_ms')::int) as avg_response_time_ms,
    COUNT(*) as answer_count
FROM llm_answers 
GROUP BY model_info->>'model_name'
ORDER BY avg_response_time_ms;
*/

-- Статистика использования скриншотов
/*
SELECT 
    COUNT(*) as total_commands,
    COUNT(CASE WHEN EXISTS (
        SELECT 1 FROM screenshots s 
        WHERE s.session_id = c.session_id
    ) THEN 1 END) as commands_with_screenshots,
    ROUND(
        COUNT(CASE WHEN EXISTS (
            SELECT 1 FROM screenshots s 
            WHERE s.session_id = c.session_id
        ) THEN 1 END) * 100.0 / COUNT(*), 2
    ) as screenshot_usage_percent
FROM commands c;
*/
