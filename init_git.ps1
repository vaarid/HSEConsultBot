# PowerShell скрипт для инициализации Git репозитория
Write-Host "Инициализация Git репозитория для проекта Amvera..." -ForegroundColor Green

# Инициализация Git репозитория
git init

# Создание ветки для Amvera
git checkout -b amvera-deployment

# Добавление всех файлов
git add .

# Коммит изменений
git commit -m "feat: адаптация проекта для развертывания на Amvera

- Создан Procfile для определения процессов
- Добавлен runtime.txt с версией Python  
- Создан envExample с примером переменных окружения
- Адаптирована конфигурация для работы с внешними сервисами
- Улучшен main.py с проверкой переменных окружения
- Создан admin_main.py для запуска админ-панели
- Обновлен requirements.txt для совместимости с Amvera
- Добавлена документация по развертыванию на Amvera"

Write-Host ""
Write-Host "Git репозиторий инициализирован!" -ForegroundColor Green
Write-Host "Ветка amvera-deployment создана и все изменения закоммичены." -ForegroundColor Green
Write-Host ""
Write-Host "Для проверки статуса выполните: git status" -ForegroundColor Yellow
Write-Host "Для просмотра истории: git log --oneline" -ForegroundColor Yellow
Write-Host ""
