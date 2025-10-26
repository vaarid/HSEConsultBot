# Команды Git для коммита изменений

Выполните следующие команды в терминале в директории проекта:

## 1. Инициализация Git репозитория (если еще не инициализирован)
```bash
git init
```

## 2. Создание ветки для Amvera
```bash
git checkout -b amvera-deployment
```

## 3. Добавление всех файлов
```bash
git add .
```

## 4. Коммит изменений
```bash
git commit -m "feat: адаптация проекта для развертывания на Amvera

- Создан Procfile для определения процессов
- Добавлен runtime.txt с версией Python
- Создан envExample с примером переменных окружения
- Адаптирована конфигурация для работы с внешними сервисами
- Улучшен main.py с проверкой переменных окружения
- Создан admin_main.py для запуска админ-панели
- Обновлен requirements.txt для совместимости с Amvera
- Добавлена документация по развертыванию на Amvera"
```

## 5. Проверка статуса
```bash
git status
```

## 6. Просмотр истории коммитов
```bash
git log --oneline
```

## 7. Переключение между ветками
```bash
# Переключиться на main
git checkout main

# Переключиться на amvera-deployment
git checkout amvera-deployment
```

## 8. Слияние веток (если нужно)
```bash
git checkout main
git merge amvera-deployment
```

## 9. Отправка в удаленный репозиторий (если настроен)
```bash
git push origin amvera-deployment
```
