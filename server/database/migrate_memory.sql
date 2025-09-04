-- =====================================================
-- МИГРАЦИЯ: ДОБАВЛЕНИЕ СИСТЕМЫ ПАМЯТИ
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
ALTER TABLE users 
ADD CONSTRAINT users_short_memory_size CHECK (LENGTH(COALESCE(short_term_memory, '')) <= 10240),
ADD CONSTRAINT users_long_memory_size CHECK (LENGTH(COALESCE(long_term_memory, '')) <= 10240);

-- Создаем функцию для очистки устаревшей краткосрочной памяти
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

-- Создаем функцию для получения статистики памяти
CREATE OR REPLACE FUNCTION get_memory_stats()
RETURNS TABLE(
    total_users BIGINT,
    users_with_memory BIGINT,
    users_with_short_memory BIGINT,
    users_with_long_memory BIGINT,
    avg_short_memory_size NUMERIC,
    avg_long_memory_size NUMERIC,
    oldest_memory_update TIMESTAMP WITH TIME ZONE,
    newest_memory_update TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_users,
        COUNT(CASE WHEN short_term_memory IS NOT NULL OR long_term_memory IS NOT NULL END)::BIGINT as users_with_memory,
        COUNT(CASE WHEN short_term_memory IS NOT NULL END)::BIGINT as users_with_short_memory,
        COUNT(CASE WHEN long_term_memory IS NOT NULL END)::BIGINT as users_with_long_memory,
        COALESCE(ROUND(AVG(LENGTH(COALESCE(short_term_memory, ''))), 0)::NUMERIC as avg_short_memory_size,
        COALESCE(ROUND(AVG(LENGTH(COALESCE(long_term_memory, ''))), 0)::NUMERIC as avg_long_memory_size,
        MIN(memory_updated_at) as oldest_memory_update,
        MAX(memory_updated_at) as newest_memory_update
    FROM users;
END;
$$ LANGUAGE plpgsql;

-- Создаем представление для удобного просмотра памяти пользователей
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

-- Добавляем комментарии к функциям и представлению
COMMENT ON FUNCTION cleanup_expired_short_term_memory(INTEGER) IS 'Очищает краткосрочную память пользователей старше указанного количества часов';
COMMENT ON FUNCTION get_memory_stats() IS 'Возвращает статистику использования системы памяти';
COMMENT ON VIEW users_memory_view IS 'Представление для просмотра памяти пользователей';

-- Проверяем, что миграция прошла успешно
DO $$
BEGIN
    -- Проверяем наличие новых полей
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name IN ('short_term_memory', 'long_term_memory', 'memory_updated_at')
    ) THEN
        RAISE EXCEPTION 'Миграция не прошла: новые поля не найдены';
    END IF;
    
    -- Проверяем наличие индексов
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'users' 
        AND indexname = 'idx_users_memory_updated'
    ) THEN
        RAISE EXCEPTION 'Миграция не прошла: индекс idx_users_memory_updated не создан';
    END IF;
    
    RAISE NOTICE 'Миграция памяти успешно завершена!';
END $$;

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

-- Поиск пользователей с активной памятью
-- SELECT hardware_id_hash, memory_updated_at 
-- FROM users 
-- WHERE short_term_memory IS NOT NULL OR long_term_memory IS NOT NULL
-- ORDER BY memory_updated_at DESC;
