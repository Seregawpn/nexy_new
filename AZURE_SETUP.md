# 🚀 Настройка Azure Container Registry и ручной деплой

## 📋 Что нужно настроить

### 1. Azure Container Registry (ACR)

```bash
# Создать Container Registry
az acr create \
  --resource-group voice-assistant-rg \
  --name voiceassistantacr \
  --sku Basic \
  --admin-enabled true

# Получить учетные данные
az acr credential show --name voiceassistantacr
```

### 2. Сборка и загрузка Docker образа

```bash
# Логинимся в ACR
az acr login --name voiceassistantacr

# Собираем образ
docker build -t voiceassistantacr.azurecr.io/voice-assistant:latest ./server

# Загружаем в ACR
docker push voiceassistantacr.azurecr.io/voice-assistant:latest
```

### 3. Обновление Container App

```bash
# Обновить Container App с новым образом
az containerapp update \
  --name nexy \
  --resource-group voice-assistant-rg \
  --image voiceassistantacr.azurecr.io/voice-assistant:latest
```

## 🔧 Процесс деплоя

### 1. Загрузка кода на GitHub:
```bash
git add .
git commit -m "Добавлен HTTP сервер на порт 80"
git push origin main
```

### 2. Сборка и деплой (вручную):
```bash
# Собрать Docker образ
docker build -t voice-assistant:latest ./server

# Загрузить в Azure Container Registry
docker tag voice-assistant:latest voiceassistantacr.azurecr.io/voice-assistant:latest
docker push voiceassistantacr.azurecr.io/voice-assistant:latest

# Обновить Container App
az containerapp update \
  --name nexy \
  --resource-group voice-assistant-rg \
  --image voiceassistantacr.azurecr.io/voice-assistant:latest
```

## 🧪 Тестирование

### 1. Проверить HTTP endpoints:
```bash
# Health check
curl https://nexy.azurecontainerapps.io/health

# Status
curl https://nexy.azurecontainerapps.io/status

# Root
curl https://nexy.azurecontainerapps.io/
```

### 2. Проверить gRPC:
```bash
# Тест gRPC подключения
grpcurl -plaintext nexy.azurecontainerapps.io:443 list
```

## 🚀 GitHub Actions

**Автоматический деплой отключен** - используется только для:
- ✅ Хранения кода
- ✅ Версионирования
- ✅ Валидации структуры проекта
- ✅ Проверки зависимостей

## 📝 Чек-лист деплоя

- [ ] Код загружен на GitHub
- [ ] Azure Container Registry создан
- [ ] Docker образ собран и загружен в ACR
- [ ] Container App обновлен с новым образом
- [ ] HTTP endpoints протестированы
- [ ] gRPC сервер работает
