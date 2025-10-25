# 🤝 Руководство по внесению вклада

Спасибо за интерес к проекту **HSEConsultBot**! Мы приветствуем любой вклад в развитие проекта.

## 🎯 Как можно помочь

### 🐛 **Сообщения об ошибках**

Если вы нашли ошибку:

1. **Проверьте** существующие [Issues](https://github.com/vaarid/HSEConsultBot/issues)
2. **Создайте** новый Issue с подробным описанием
3. **Укажите** шаги для воспроизведения ошибки
4. **Приложите** логи и скриншоты (если применимо)

### 💡 **Предложения улучшений**

Для новых функций:

1. **Обсудите** идею в [Issues](https://github.com/vaarid/HSEConsultBot/issues)
2. **Опишите** проблему, которую решает предложение
3. **Предложите** конкретное решение
4. **Учтите** влияние на существующую функциональность

### 🔧 **Pull Requests**

Для внесения изменений в код:

## 🚀 Процесс разработки

### 1. **Fork репозитория**

```bash
# Перейдите на GitHub и нажмите "Fork"
# Затем клонируйте ваш fork
git clone https://github.com/YOUR_USERNAME/HSEConsultBot.git
cd HSEConsultBot
```

### 2. **Настройка окружения**

```bash
# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt

# Настройте переменные окружения
cp .envExample .env
# Отредактируйте .env файл
```

### 3. **Создание feature branch**

```bash
# Создайте новую ветку для вашей функции
git checkout -b feature/amazing-feature
# или
git checkout -b fix/bug-description
```

### 4. **Разработка**

- **Следуйте** стилю кода проекта
- **Добавляйте** тесты для новой функциональности
- **Обновляйте** документацию при необходимости
- **Проверяйте** работу через Docker

### 5. **Тестирование**

```bash
# Запустите тесты
python -m pytest

# Проверьте линтеры
flake8 .
black --check .

# Запустите бота локально
docker-compose up -d
```

### 6. **Commit и Push**

```bash
# Добавьте изменения
git add .

# Создайте commit с описательным сообщением
git commit -m "feat: add amazing feature"
# или
git commit -m "fix: resolve bug in user authentication"

# Push в ваш fork
git push origin feature/amazing-feature
```

### 7. **Создание Pull Request**

1. **Перейдите** на GitHub в ваш fork
2. **Нажмите** "Compare & pull request"
3. **Заполните** шаблон Pull Request
4. **Дождитесь** review от maintainers

## 📝 Стандарты кода

### **Python Style Guide**

- **PEP 8** - основной стиль
- **Black** - автоматическое форматирование
- **Flake8** - проверка стиля
- **Type hints** - типизация функций

### **Структура коммитов**

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: resolve bug
docs: update documentation
style: formatting changes
refactor: code refactoring
test: add tests
chore: maintenance tasks
```

### **Примеры:**

```bash
feat: add GigaChat integration
fix: resolve memory leak in Redis connection
docs: update API documentation
test: add unit tests for analytics module
```

## 🧪 Тестирование

### **Типы тестов**

- **Unit tests** - тестирование отдельных функций
- **Integration tests** - тестирование взаимодействия компонентов
- **E2E tests** - тестирование полного пользовательского сценария

### **Запуск тестов**

```bash
# Все тесты
python -m pytest

# Конкретный тест
python -m pytest tests/test_analytics.py

# С покрытием
python -m pytest --cov=src
```

## 📚 Документация

### **Обновление документации**

При добавлении новой функциональности:

1. **Обновите** README.md если нужно
2. **Добавьте** docstrings к функциям
3. **Создайте** примеры использования
4. **Обновите** API документацию

### **Структура docstring**

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Краткое описание функции
    
    Args:
        param1: Описание первого параметра
        param2: Описание второго параметра
        
    Returns:
        bool: Описание возвращаемого значения
        
    Raises:
        ValueError: Когда параметр неверный
        
    Example:
        >>> example_function("test", 123)
        True
    """
    pass
```

## 🔒 Безопасность

### **Обработка секретов**

- **Никогда** не коммитьте `.env` файлы
- **Используйте** `.envExample` для примеров
- **Не добавляйте** API ключи в код
- **Проверяйте** `.gitignore` перед коммитом

### **GDPR и персональные данные**

- **Анонимизируйте** данные в тестах
- **Не используйте** реальные персональные данные
- **Следуйте** принципам ФЗ-152
- **Проверяйте** анонимизацию в аналитике

## 🏷️ Release Process

### **Версионирование**

Используем [Semantic Versioning](https://semver.org/):

- **MAJOR** - breaking changes
- **MINOR** - новые функции (backward compatible)
- **PATCH** - исправления багов

### **Примеры версий:**

- `1.0.0` - первая стабильная версия
- `1.1.0` - добавлена новая функция
- `1.1.1` - исправлен баг
- `2.0.0` - breaking changes

## 🤔 Часто задаваемые вопросы

### **Q: Как добавить новый AI провайдер?**

A: Создайте новый класс в `ai/` директории, наследуя от `BaseAIClient`, и добавьте его в `AIClientFactory`.

### **Q: Как добавить новую команду бота?**

A: Создайте новый handler в `bot/handlers/` и зарегистрируйте его в `bot/handlers/__init__.py`.

### **Q: Как обновить базу знаний?**

A: Отредактируйте `faq_ohs_ru_links.json` файл, следуя существующей структуре.

## 📞 Получение помощи

- **GitHub Issues** - для багов и предложений
- **Discussions** - для общих вопросов
- **Telegram** - [@vaarid](https://t.me/vaarid) для быстрой связи

## 🎉 Спасибо!

Каждый вклад важен для развития проекта. Спасибо за помощь в создании лучшего AI-консультанта по охране труда!

---

**Made with ❤️ by the HSEConsultBot community**
