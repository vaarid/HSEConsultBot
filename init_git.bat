@echo off
echo Инициализация Git репозитория для проекта Amvera...

REM Инициализация Git репозитория
git init

REM Создание ветки для Amvera
git checkout -b amvera-deployment

REM Добавление всех файлов
git add .

REM Коммит изменений
git commit -m "feat: адаптация проекта для развертывания на Amvera

- Создан Procfile для определения процессов
- Добавлен runtime.txt с версией Python  
- Создан envExample с примером переменных окружения
- Адаптирована конфигурация для работы с внешними сервисами
- Улучшен main.py с проверкой переменных окружения
- Создан admin_main.py для запуска админ-панели
- Обновлен requirements.txt для совместимости с Amvera
- Добавлена документация по развертыванию на Amvera"

echo.
echo Git репозиторий инициализирован!
echo Ветка amvera-deployment создана и все изменения закоммичены.
echo.
echo Для проверки статуса выполните: git status
echo Для просмотра истории: git log --oneline
echo.
pause
