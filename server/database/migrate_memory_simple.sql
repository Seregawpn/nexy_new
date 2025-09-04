-- =====================================================
-- УПРОЩЕННАЯ МИГРАЦИЯ: ДОБАВЛЕНИЕ СИСТЕМЫ ПАМЯТИ
-- =====================================================
-- Дата: 2024-12-19
-- Описание: Добавляем поля для краткосрочной и долгосрочной памяти пользователя
-- =====================================================

BEGIN;

-- Добавляем поля для памяти в таблицу users
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS short_term_memory TEXT,
ADD COLUMN IF NOT EXISTS long_term_memory TEXT,
ADD COLUMN IF NOT EXISTS memory_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Добавляем комментарии для документации
COMMENT ON COLUMN users.short_term_memory IS 'Краткосрочная память пользователя - контекст текущего разговора';
COMMENT ON COLUMN users.long_term_memory IS 'Долгосрочная память пользователя - важная информация для запоминания';
COMMENT ON COLUMN users.memory_updated_at IS 'Время последнего обновления памяти';

-- Создаем индекс для быстрого поиска по времени обновления памяти
CREATE INDEX IF NOT EXISTS idx_users_memory_updated ON users(memory_updated_at);

-- Создаем индекс для поиска пользователей с активной памятью
CREATE INDEX IF NOT EXISTS idx_users_active_memory ON users(hardware_id_hash) 
WHERE short_term_memory IS NOT NULL OR long_term_memory IS NOT NULL;

-- Добавляем ограничение на размер памяти (максимум 10KB для каждого поля)
-- Используем DO блок для безопасного добавления ограничений
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'users_short_memory_size'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_short_memory_size 
        CHECK (LENGTH(COALESCE(short_term_memory, '')) <= 10240);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'users_long_memory_size'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_long_memory_size 
        CHECK (LENGTH(COALESCE(long_term_memory, '')) <= 10240);
    END IF;
END $$;

-- Создаем простую функцию для очистки устаревшей краткосрочной памяти
CREATE OR REPLACE FUNCTION cleanup_expired_short_term_memory(hours_old INTEGER DEFAULT 24)
RETURNS INTEGER AS $$
DECLARE
    affected_rows INTEGER;
BEGIN
    UPDATE users 
    SET short_term_memory = NULL,
        memory_updated_at = NOW()
    WHERE short_term_memory IS NOT NULL 
      AND memory_updated_at < NOW() - INTERVAL '1 hour' * hours_old;
    
    GET DIAGNOSTICS affected_rows = ROW_COUNT;
    
    RETURN affected_rows;
END;
$$ LANGUAGE plpgsql;

-- Создаем простую функцию для получения статистики памяти
CREATE OR REPLACE FUNCTION get_memory_stats()
RETURNS TABLE(
    total_users BIGINT,
    users_with_memory BIGINT,
    users_with_short_memory BIGINT,
    users_with_long_memory BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_users,
        COUNT(CASE WHEN short_term_memory IS NOT NULL OR long_term_memory IS NOT NULL END)::BIGINT as users_with_memory,
        COUNT(CASE WHEN short_term_memory IS NOT NULL END)::BIGINT as users_with_short_memory,
        COUNT(CASE WHEN long_term_memory IS NOT NULL END)::BIGINT as users_with_long_memory
    FROM users;
END;
$$ LANGUAGE plpgsql;

-- Создаем простое представление для просмотра памяти пользователей
CREATE OR REPLACE VIEW users_memory_view AS
SELECT 
    u.hardware_id_hash,
    u.created_at,
    u.memory_updated_at,
    CASE 
        WHEN u.short_term_memory IS NOT NULL THEN LENGTH(u.short_term_memory)
        ELSE 0 
    END as short_memory_size,
    CASE 
        WHEN u.long_term_memory IS NOT NULL THEN LENGTH(u.long_term_memory)
        ELSE 0 
    END as long_memory_size,
    u.short_term_memory,
    u.long_term_memory
FROM users u
WHERE u.short_term_memory IS NOT NULL OR u.long_term_memory IS NOT NULL
ORDER BY u.memory_updated_at DESC;

-- Добавляем комментарии
COMMENT ON FUNCTION cleanup_expired_short_term_memory(INTEGER) IS 'Очищает краткосрочную память пользователей старше указанного количества часов';
COMMENT ON FUNCTION get_memory_stats() IS 'Возвращает статистику использования системы памяти';
COMMENT ON VIEW users_memory_view IS 'Представление для просмотра памяти пользователей';

COMMIT;

-- =====================================================
-- ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
-- =====================================================

-- Очистка краткосрочной памяти старше 12 часов
-- SELECT cleanup_expired_short_term_memory(12);

-- Получение статистики памяти
-- SELECT * FROM get_memory_stats();

-- Просмотр памяти пользователей
-- SELECT * FROM users_memory_view LIMIT 10;
