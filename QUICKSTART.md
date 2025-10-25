# 🚀 Быстрый старт проекта

Telegram бот для консультаций по охране труда и технике безопасности в ДОУ.

## 📋 Предварительные требования

- Docker и Docker Compose
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))
- OpenAI API Key (получить на [platform.openai.com](https://platform.openai.com))

## ⚡ Запуск за 3 шага

### 1️⃣ Настройте переменные окружения

Скопируйте файл `.envExample` и переименуйте в `.env`:

```bash
cp .envExample .env
```

Откройте `.env` и заполните **обязательные** параметры:

```env
# Обязательно заполнить:
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here

# Рекомендуется изменить:
POSTGRES_PASSWORD=your_strong_password
ADMIN_SECRET_KEY=your_secret_key_32_chars_min
ENCRYPTION_KEY=your_32_character_key_here

# ID администраторов (через запятую):
ADMIN_USER_IDS=123456789
```

### 2️⃣ Запустите Docker контейнеры

```bash
docker-compose up -d
```

Проверьте статус:

```bash
docker-compose ps
```

Должны быть запущены 4 контейнера:
- `ot_bot_postgres` - База данных
- `ot_bot_redis` - Кэш
- `ot_bot` - Telegram бот
- `ot_bot_admin` - Админ-панель

### 3️⃣ Откройте админ-панель

Админ-панель доступна по адресу: http://localhost:8000

**Логин:** `admin`  
**Пароль:** первые 20 символов из `ADMIN_SECRET_KEY`

## 📊 Просмотр логов

```bash
# Логи бота
docker-compose logs -f bot

# Логи всех сервисов
docker-compose logs -f
```

## 🛑 Остановка проекта

```bash
docker-compose down
```

## 🔧 Полезные команды

```bash
# Перезапуск бота после изменений
docker-compose restart bot

# Пересборка контейнеров
docker-compose up -d --build

# Очистка всех данных
docker-compose down -v
```

## 📖 Создание бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите название бота (например: "OT Consultant Bot")
4. Введите username бота (например: "ot_consultant_bot")
5. Скопируйте полученный токен в `.env`

## 🔑 Получение OpenAI API Key

1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com)
2. Перейдите в [API Keys](https://platform.openai.com/api-keys)
3. Создайте новый ключ
4. Скопируйте его в `.env`

## 🎯 Основные команды бота

**Базовые команды:**
- `/start` - Начало работы
- `/help` - Справка
- `/stats` - Статистика
- `/admin` - Админ-панель (только для администраторов)
- `/gdpr` - Управление персональными данными

**Работа с вопросами:**
- `/ask` - Задать вопрос (обычный режим)
- `/ask_assistant` - Задать вопрос нейроассистенту 🤖
- `? ваш вопрос` - Быстрый вопрос нейроассистенту

**Нейроассистент:**
- `/assistant_info` - Информация о нейроассистенте
- `/reset_thread` - Начать новый диалог

## 🔄 Переключение на GigaChat

Если хотите использовать GigaChat вместо OpenAI:

1. Получите API ключ на [developers.sber.ru](https://developers.sber.ru/portal/products/gigachat)
2. Добавьте в `.env`:
   ```env
   AI_PROVIDER=gigachat
   GIGACHAT_API_KEY=your_gigachat_key
   ```
3. Перезапустите бот: `docker-compose restart bot`

## ❗ Решение проблем

### Бот не отвечает

```bash
# Проверьте логи
docker-compose logs bot

# Проверьте, что токен правильный
# Проверьте, что бот запущен
docker-compose ps
```

### Ошибка подключения к базе данных

```bash
# Пересоздайте контейнеры
docker-compose down
docker-compose up -d
```

### Не могу войти в админ-панель

Убедитесь, что используете правильный пароль (первые 20 символов `ADMIN_SECRET_KEY`).

## 📚 Дальнейшая настройка

См. [README.md](README.md) для подробной документации.

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все переменные окружения заполнены
3. Проверьте, что порты 5432, 6379, 8000 не заняты другими приложениями

