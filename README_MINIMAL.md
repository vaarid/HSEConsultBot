# 📋 Минимальный набор файлов для GitHub

## ✅ **Обязательные файлы**

### 📄 **Основные**
- `README.md` - главное описание проекта
- `LICENSE` - лицензия MIT
- `requirements.txt` - зависимости Python
- `docker-compose.yml` - конфигурация Docker
- `Dockerfile` - образ контейнера
- `.envExample` - пример переменных окружения
- `.gitignore` - исключения для Git

### 📚 **Документация**
- `QUICKSTART.md` - быстрый старт
- `ASSISTANT_GUIDE.md` - работа с нейроассистентом
- `CONTRIBUTING.md` - руководство по вкладу
- `CHANGELOG.md` - история изменений

### 🤖 **Основной код**
- `main.py` - точка входа
- `bot/` - код Telegram бота
- `ai/` - AI клиенты
- `database/` - модели и CRUD
- `services/` - бизнес-логика
- `utils/` - утилиты
- `admin/` - веб-админка

### 📊 **База знаний**
- `faq_ohs_ru_links.json` - основная база знаний (250+ вопросов)

## ❌ **Файлы для исключения**

### 📝 **Анализ и описание**
- `PROJECT_ANALYSIS.md` - анализ соответствия ТЗ
- `Описание.md` - техническое задание
- `PROJECT_OVERVIEW.md` - детальный обзор
- `IMPROVEMENTS_ROADMAP.md` - план развития
- `PRIVACY_PROTECTION.md` - защита ПД
- `KNOWLEDGE_BASE_INTEGRATION.md` - интеграция БЗ

### 🧪 **Тестирование и разработка**
- `test_knowledge_base.py` - тесты БЗ
- `expand_faq.py` - расширение FAQ
- `json_to_csv.py` - конвертация данных
- `faq_ohs_ru_links_extended.json` - расширенная БЗ

### 🔧 **Временные файлы**
- `logs/` - логи (кроме .gitkeep)
- `*.log` - файлы логов
- `.env` - секретные ключи

## 🎯 **Итоговый размер репозитория**

**Минимальный набор:** ~2-3 MB
- Основной код: ~500 KB
- База знаний: ~120 KB  
- Документация: ~100 KB
- Docker файлы: ~50 KB

**Исключенные файлы:** ~5-10 MB
- Анализ проекта: ~2 MB
- Расширенная БЗ: ~3 MB
- Логи и тесты: ~2 MB
- Временные файлы: ~1 MB

## 🚀 **Команды для подготовки к GitHub**

```bash
# 1. Удалить файлы анализа
rm PROJECT_ANALYSIS.md
rm Описание.md
rm PROJECT_OVERVIEW.md
rm IMPROVEMENTS_ROADMAP.md
rm PRIVACY_PROTECTION.md
rm KNOWLEDGE_BASE_INTEGRATION.md

# 2. Удалить файлы разработки
rm test_knowledge_base.py
rm expand_faq.py
rm json_to_csv.py
rm faq_ohs_ru_links_extended.json

# 3. Очистить логи
rm -rf logs/*
touch logs/.gitkeep

# 4. Проверить .gitignore
git status
```

## 📦 **Структура для GitHub**

```
HSEConsultBot/
├── 📄 README.md
├── 📄 LICENSE
├── 📄 requirements.txt
├── 📄 docker-compose.yml
├── 📄 Dockerfile
├── 📄 .envExample
├── 📄 .gitignore
├── 📄 QUICKSTART.md
├── 📄 ASSISTANT_GUIDE.md
├── 📄 CONTRIBUTING.md
├── 📄 CHANGELOG.md
├── 🤖 main.py
├── 📁 bot/
├── 📁 ai/
├── 📁 database/
├── 📁 services/
├── 📁 utils/
├── 📁 admin/
├── 📁 knowledge_base/
├── 📄 faq_ohs_ru_links.json
└── 📁 logs/ (только .gitkeep)
```

**Итого: ~15-20 файлов, ~2-3 MB**
