# 📋 Полный обзор проекта HSEConsultBot

## 🎯 Миссия проекта

**HSEConsultBot** - это интеллектуальный Telegram-бот для специалистов по охране труда, который предоставляет юридические консультации на основе актуального законодательства РФ с использованием современных AI-технологий.

### 🌟 **Ключевые цели**

- **Демократизация знаний** - доступ к экспертным консультациям для всех специалистов ОТ
- **Повышение безопасности** - снижение рисков через качественные консультации
- **Соответствие законодательству** - актуальная информация по ФЗ-152, ТК РФ, СанПиН
- **Инновации в образовании** - использование AI для обучения и консультаций

## 🏗️ Архитектура системы

### 📐 **Высокоуровневая архитектура**

```
┌─────────────────────────────────────────────────────────┐
│                    Пользователь                         │
│                 (Telegram Client)                       │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTPS/WebSocket
                  ▼
┌─────────────────────────────────────────────────────────┐
│                Telegram Bot API                         │
│                  (aiogram 3.x)                         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              Application Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Handlers   │  │ Middlewares │  │    States    │    │
│  │              │  │             │  │   (FSM)      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────────┐  ┌────────────────────────┐
│   AI Services    │  │   Data Layer           │
│  ┌────────────┐  │  │  ┌──────────────────┐  │
│  │   OpenAI   │  │  │  │   PostgreSQL     │  │
│  │   API      │  │  │  │   (Primary DB)   │  │
│  ├────────────┤  │  │  └──────────────────┘  │
│  │   GigaChat │  │  │  ┌──────────────────┐  │
│  │   API      │  │  │  │     Redis        │  │
│  └────────────┘  │  │  │   (Cache/FSM)    │  │
└──────────────────┘  │  └──────────────────┘  │
                      └────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│         Admin Panel (FastAPI)            │
│      http://localhost:8000              │
└──────────────────────────────────────────┘
```

### 🔧 **Технологический стек**

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| **Bot Framework** | aiogram | 3.x | Telegram Bot API |
| **Web Framework** | FastAPI | Latest | Admin Panel & API |
| **Database** | PostgreSQL | 15 | Основная БД |
| **Cache** | Redis | 7 | FSM & кэширование |
| **AI Providers** | OpenAI, GigaChat | Latest | ИИ-консультации |
| **ORM** | SQLAlchemy | 2.0 | Работа с БД |
| **Containerization** | Docker | Latest | Развертывание |
| **Logging** | Loguru | Latest | Логирование |
| **Analytics** | Custom | - | Аналитика |

## 🎭 Роли пользователей

### 👑 **Администратор**
- **Доступ:** Полный контроль системы
- **Функции:** Управление пользователями, аналитика, настройки
- **Интерфейс:** Веб-панель + команды бота

### 🛡️ **Специалист ОТ в ДОУ**
- **Доступ:** Расширенные консультации
- **Функции:** Нейроассистент, база знаний, статистика
- **Особенности:** Персонализированные промпты для ДОУ

### 🏢 **Специалист ОТ (другие отрасли)**
- **Доступ:** Стандартные консультации
- **Функции:** Обычный режим, нейроассистент
- **Особенности:** Универсальные промпты

### 👤 **Сотрудник**
- **Доступ:** Базовые консультации
- **Функции:** Обычный режим, ограниченная статистика
- **Особенности:** Упрощенные ответы

### 🆓 **Пробный пользователь**
- **Доступ:** Ограниченные функции
- **Функции:** Базовые консультации
- **Ограничения:** Лимит запросов

## 🤖 AI-интеграция

### 🧠 **Мульти-провайдерная архитектура**

#### **OpenAI (Основной)**
- **GPT-4** - для сложных консультаций
- **GPT-3.5-turbo** - для быстрых ответов
- **Assistants API** - нейроассистент с базой знаний
- **Fallback** - при недоступности других провайдеров

#### **GigaChat (Российский)**
- **GigaChat Pro** - российская альтернатива
- **Специализация** - российское законодательство
- **Преимущества** - лучшая локализация

#### **Автоматический выбор**
```python
# Логика выбора провайдера
if openai_available and user_preference == "openai":
    use_openai()
elif gigachat_available and user_preference == "gigachat":
    use_gigachat()
else:
    use_fallback_provider()
```

### 🔄 **Режимы работы**

#### **Обычный режим** (`/ask`)
- **Быстрые ответы** через Chat Completions API
- **Без контекста** - каждый запрос независим
- **Оптимизация** - минимальное время ответа
- **Использование** - простые вопросы

#### **Нейроассистент** (`/ask_assistant`)
- **Контекстные диалоги** с сохранением истории
- **База знаний** - доступ к документам
- **Персонализация** - адаптация под роль пользователя
- **Использование** - сложные консультации

## 📚 База знаний

### 📖 **Структура документов**

```
knowledge_base/
├── labor_law/           # Трудовое право
│   ├── tk_rf/          # Трудовой кодекс РФ
│   ├── federal_laws/   # Федеральные законы
│   └── regulations/    # Подзаконные акты
├── safety/             # Охрана труда
│   ├── sanpin/        # СанПиН
│   ├── gost/          # ГОСТы
│   └── instructions/ # Инструкции
├── dou_specific/      # Специфика ДОУ
│   ├── children_safety/ # Безопасность детей
│   ├── premises/      # Помещения
│   └── equipment/     # Оборудование
└── templates/         # Шаблоны документов
    ├── instructions/  # Инструкции по ОТ
    ├── protocols/     # Протоколы
    └── reports/       # Отчеты
```

### 🔍 **Система поиска**

#### **Семантический поиск**
- **OpenAI Embeddings** - векторное представление
- **Cosine Similarity** - поиск по схожести
- **Relevance Scoring** - ранжирование результатов

#### **Ключевые слова**
- **TF-IDF** - частотный анализ
- **Stemming** - приведение к корню
- **Synonyms** - обработка синонимов

#### **Фильтрация**
- **По категориям** - тематическая фильтрация
- **По актуальности** - проверка дат
- **По релевантности** - порог схожести

## 🗄️ База данных

### 📊 **Схема данных**

#### **Основные таблицы**

```sql
-- Пользователи
users (
    id BIGINT PRIMARY KEY,           -- Telegram User ID
    username VARCHAR(255),          -- @username
    first_name VARCHAR(255),         -- Имя
    last_name VARCHAR(255),          -- Фамилия
    role ENUM,                      -- Роль пользователя
    gdpr_accepted BOOLEAN,          -- Согласие ФЗ-152
    assistant_thread_id VARCHAR(255), -- OpenAI Thread ID
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Сообщения (история диалогов)
messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    role VARCHAR(50),               -- user/assistant/system
    content TEXT,                   -- Содержимое сообщения
    created_at TIMESTAMP
);

-- Запросы (для аналитики)
queries (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    question TEXT,                  -- Вопрос пользователя
    answer TEXT,                    -- Ответ AI
    ai_provider ENUM,               -- OpenAI/GigaChat
    ai_model VARCHAR(100),         -- Модель AI
    response_time FLOAT,           -- Время ответа
    tokens_used INTEGER,           -- Использованные токены
    category VARCHAR(100),          -- Категория вопроса
    documents_used JSON,            -- Использованные документы
    created_at TIMESTAMP
);

-- Документы базы знаний
documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),             -- Название документа
    description TEXT,               -- Описание
    doc_type VARCHAR(100),          -- Тип документа
    url VARCHAR(1000),              -- Ссылка на документ
    file_path VARCHAR(500),         -- Путь к файлу
    openai_file_id VARCHAR(255),    -- OpenAI File ID
    content TEXT,                   -- Содержимое
    tags JSON,                      -- Теги
    is_active BOOLEAN,              -- Активность
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Логи аудита (ФЗ-152)
audit_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,                 -- ID пользователя
    action VARCHAR(100),            -- Действие
    details JSON,                   -- Детали
    ip_address VARCHAR(45),         -- IP адрес
    user_agent VARCHAR(500),        -- User Agent
    created_at TIMESTAMP
);
```

### 🔄 **Связи между таблицами**

```mermaid
erDiagram
    users ||--o{ messages : "has many"
    users ||--o{ queries : "has many"
    users ||--o{ audit_logs : "has many"
    
    users {
        bigint id PK
        string username
        string first_name
        string last_name
        enum role
        boolean gdpr_accepted
        string assistant_thread_id
        timestamp created_at
    }
    
    messages {
        int id PK
        bigint user_id FK
        string role
        text content
        timestamp created_at
    }
    
    queries {
        int id PK
        bigint user_id FK
        text question
        text answer
        enum ai_provider
        string ai_model
        float response_time
        int tokens_used
        string category
        json documents_used
        timestamp created_at
    }
    
    documents {
        int id PK
        string title
        text description
        string doc_type
        string url
        string file_path
        string openai_file_id
        text content
        json tags
        boolean is_active
        timestamp created_at
    }
    
    audit_logs {
        int id PK
        bigint user_id
        string action
        json details
        string ip_address
        string user_agent
        timestamp created_at
    }
```

## 📊 Аналитика и мониторинг

### 📈 **Собираемые метрики**

#### **Пользовательская активность**
- Количество активных пользователей
- Частота использования бота
- Время сессий
- Популярные функции

#### **AI-производительность**
- Время ответа по провайдерам
- Использование токенов
- Качество ответов (оценки пользователей)
- Частота ошибок

#### **Контент-аналитика**
- Популярные темы консультаций
- Сложность вопросов
- Эффективность базы знаний
- Пробелы в знаниях

### 🛡️ **Анонимизация данных**

#### **Автоматическая анонимизация**
```python
# Примеры анонимизации
"Иванов Иван Иванович" → "[ФИО]"
"+7 (999) 123-45-67" → "[ТЕЛЕФОН]"
"user@example.com" → "[EMAIL]"
"1234 567890" → "[ПАСПОРТ]"
```

#### **GDPR-совместимые отчеты**
- Полное удаление персональных данных
- Анонимизированная аналитика
- Контролируемый экспорт данных
- Журнал всех операций

## 🔐 Безопасность

### 🛡️ **Многоуровневая защита**

#### **Уровень 1: Сетевая безопасность**
- HTTPS/TLS для всех соединений
- VPN для административного доступа
- Firewall правила
- DDoS защита

#### **Уровень 2: Аутентификация**
- Telegram OAuth (встроенная)
- JWT токены для API
- Роль-ориентированный доступ
- Сессионное управление

#### **Уровень 3: Шифрование данных**
- Шифрование в БД (AES-256)
- Шифрование логов
- Безопасное хранение ключей
- Регулярная ротация ключей

#### **Уровень 4: Мониторинг**
- Логирование всех действий
- Обнаружение аномалий
- Алерты безопасности
- Регулярные аудиты

### 🔒 **Соответствие ФЗ-152**

#### **Принципы обработки ПД**
- **Законность** - согласие на обработку
- **Справедливость** - прозрачность целей
- **Минимальность** - только необходимые данные
- **Актуальность** - актуальные данные
- **Безопасность** - защита от утечек

#### **Права субъектов ПД**
- **Право на информацию** - что собирается
- **Право на доступ** - просмотр данных
- **Право на исправление** - изменение данных
- **Право на удаление** - "право на забвение"
- **Право на ограничение** - ограничение обработки

## 🚀 Развертывание

### 🐳 **Docker-контейнеризация**

#### **Основные сервисы**
```yaml
services:
  bot:
    build: .
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=hseconsultbot
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  admin:
    build: .
    command: python admin/web_app.py
    ports:
      - "8000:8000"
    depends_on:
      - postgres
```

#### **Переменные окружения**
```bash
# Обязательные
TELEGRAM_BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
POSTGRES_PASSWORD=your_db_password

# Опциональные
GIGACHAT_API_KEY=your_gigachat_key
AI_PROVIDER=openai
ADMIN_SECRET_KEY=your_admin_secret
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://user:pass@postgres:5432/hseconsultbot
```

### 📋 **Процесс развертывания**

#### **1. Подготовка**
```bash
# Клонирование репозитория
git clone https://github.com/vaarid/HSEConsultBot.git
cd HSEConsultBot

# Настройка переменных
cp .envExample .env
nano .env  # Заполните необходимые ключи
```

#### **2. Запуск**
```bash
# Запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f bot
```

#### **3. Инициализация**
```bash
# Создание таблиц БД
docker-compose exec bot python -c "from database.db import create_tables; create_tables()"

# Загрузка базы знаний
docker-compose exec bot python -c "from services.knowledge_base import load_documents; load_documents()"
```

## 🔄 Жизненный цикл разработки

### 🛠️ **Этапы разработки**

#### **MVP (Минимально жизнеспособный продукт)**
- ✅ Базовый Telegram-бот
- ✅ Интеграция с OpenAI
- ✅ Простая база знаний
- ✅ Базовые команды

#### **v1.0 (Текущая версия)**
- ✅ Нейроассистент с OpenAI Assistants API
- ✅ Мульти-AI интеграция (OpenAI + GigaChat)
- ✅ Система ролей пользователей
- ✅ Аналитика и статистика
- ✅ Соответствие ФЗ-152
- ✅ Веб-панель администратора

#### **v2.0 (Планируется)**
- 🔄 Загрузка документов через бота
- 🔄 Интеграция с Гарант.онлайн
- 🔄 RAG для локальных документов
- 🔄 Голосовые запросы
- 🔄 Telegram Mini App

### 🧪 **Тестирование**

#### **Типы тестов**
- **Unit тесты** - тестирование отдельных функций
- **Integration тесты** - тестирование интеграций
- **E2E тесты** - тестирование полных сценариев
- **Load тесты** - тестирование производительности

#### **Автоматизация**
- **CI/CD** - автоматическое тестирование
- **Code Quality** - линтеры и форматтеры
- **Security** - проверки безопасности
- **Performance** - мониторинг производительности

## 📈 Планы развития

### 🎯 **Краткосрочные цели (3-6 месяцев)**

#### **Функциональные улучшения**
- [ ] **Загрузка документов** через бота
- [ ] **Интеграция с Гарант.онлайн** API
- [ ] **RAG для локальных** документов
- [ ] **Голосовые запросы** (speech-to-text)
- [ ] **Telegram Mini App** для веб-интерфейса

#### **Технические улучшения**
- [ ] **Кэширование** ответов AI
- [ ] **Оптимизация** производительности
- [ ] **Мониторинг** в реальном времени
- [ ] **Автоматическое** масштабирование

### 🚀 **Долгосрочные цели (6-12 месяцев)**

#### **Монетизация**
- [ ] **Система платежей** для премиум-функций
- [ ] **Подписки** на расширенные возможности
- [ ] **Корпоративные** тарифы
- [ ] **API** для интеграций

#### **Расширение функциональности**
- [ ] **Email отчеты** для администраторов
- [ ] **Mobile приложение** (React Native)
- [ ] **Интеграция с 1С** для корпоративных клиентов
- [ ] **Мультиязычность** (английский, другие языки)

### 🌍 **Масштабирование**

#### **Географическое расширение**
- [ ] **Региональные** версии для разных стран
- [ ] **Локализация** под местное законодательство
- [ ] **Партнерства** с местными организациями

#### **Техническое масштабирование**
- [ ] **Микросервисная** архитектура
- [ ] **Kubernetes** для оркестрации
- [ ] **Multi-region** развертывание
- [ ] **CDN** для статического контента

## 🤝 Сообщество и вклад

### 👥 **Участие в разработке**

#### **Для разработчиков**
- **Fork** репозитория
- **Feature branches** для новых функций
- **Pull Requests** с описанием изменений
- **Code Review** процесса

#### **Для пользователей**
- **Bug Reports** через Issues
- **Feature Requests** с обоснованием
- **User Feedback** для улучшений
- **Testing** новых версий

### 📚 **Документация**

#### **Техническая документация**
- [README.md](README.md) - Основная документация
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт
- [ASSISTANT_GUIDE.md](ASSISTANT_GUIDE.md) - Работа с нейроассистентом
- [PRIVACY_PROTECTION.md](PRIVACY_PROTECTION.md) - Защита персональных данных
- [IMPROVEMENTS_ROADMAP.md](IMPROVEMENTS_ROADMAP.md) - План развития

#### **API документация**
- **Swagger UI** - http://localhost:8000/docs
- **OpenAPI Schema** - http://localhost:8000/openapi.json
- **Postman Collection** - для тестирования API

## 📞 Поддержка и контакты

### 🆘 **Техническая поддержка**

- **GitHub Issues** - [Создать issue](https://github.com/vaarid/HSEConsultBot/issues)
- **Telegram** - [@vaarid](https://t.me/vaarid)
- **Email** - vaarid@example.com
- **Документация** - [GitHub Wiki](https://github.com/vaarid/HSEConsultBot/wiki)

### 💬 **Сообщество**

- **Telegram канал** - [@hseconsultbot](https://t.me/hseconsultbot)
- **Discord сервер** - [Присоединиться](https://discord.gg/hseconsultbot)
- **Reddit** - [r/hseconsultbot](https://reddit.com/r/hseconsultbot)

---

**🚀 HSEConsultBot - Будущее консультаций по охране труда уже здесь!**

*Создано с ❤️ для специалистов по охране труда в дошкольных образовательных учреждениях*
