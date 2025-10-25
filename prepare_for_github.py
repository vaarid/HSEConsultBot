#!/usr/bin/env python3
"""
Скрипт для подготовки проекта к выгрузке на GitHub
Удаляет ненужные файлы и создает минимальную структуру
"""

import os
import shutil
from pathlib import Path

def remove_file(file_path):
    """Удалить файл если он существует"""
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"✅ Удален: {file_path}")
    else:
        print(f"⚠️  Не найден: {file_path}")

def remove_directory(dir_path):
    """Удалить директорию если она существует"""
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
        print(f"✅ Удалена директория: {dir_path}")
    else:
        print(f"⚠️  Директория не найдена: {dir_path}")

def create_gitkeep(file_path):
    """Создать .gitkeep файл"""
    with open(file_path, 'w') as f:
        f.write("# Keep this directory in Git\n")
    print(f"✅ Создан: {file_path}")

def main():
    """Основная функция подготовки к GitHub"""
    print("🚀 Подготовка проекта HSEConsultBot к GitHub...")
    print("=" * 50)
    
    # Файлы анализа и описания
    print("\n📝 Удаление файлов анализа...")
    analysis_files = [
        "PROJECT_ANALYSIS.md",
        "Описание.md", 
        "PROJECT_OVERVIEW.md",
        "IMPROVEMENTS_ROADMAP.md",
        "PRIVACY_PROTECTION.md",
        "KNOWLEDGE_BASE_INTEGRATION.md"
    ]
    
    for file in analysis_files:
        remove_file(file)
    
    # Файлы разработки и тестирования
    print("\n🧪 Удаление файлов разработки...")
    dev_files = [
        "test_knowledge_base.py",
        "expand_faq.py", 
        "json_to_csv.py",
        "faq_ohs_ru_links_extended.json",
        "README_MINIMAL.md",
        "prepare_for_github.py"
    ]
    
    for file in dev_files:
        remove_file(file)
    
    # Очистка логов
    print("\n📊 Очистка логов...")
    if os.path.exists("logs"):
        # Удаляем все файлы в logs, кроме .gitkeep
        for file in os.listdir("logs"):
            if file != ".gitkeep":
                file_path = os.path.join("logs", file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"✅ Удален лог: {file}")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"✅ Удалена директория логов: {file}")
        
        # Создаем .gitkeep если его нет
        gitkeep_path = os.path.join("logs", ".gitkeep")
        if not os.path.exists(gitkeep_path):
            create_gitkeep(gitkeep_path)
    else:
        # Создаем директорию logs с .gitkeep
        os.makedirs("logs", exist_ok=True)
        create_gitkeep("logs/.gitkeep")
    
    # Проверяем обязательные файлы
    print("\n✅ Проверка обязательных файлов...")
    required_files = [
        "README.md",
        "LICENSE", 
        "requirements.txt",
        "docker-compose.yml",
        "Dockerfile",
        ".envExample",
        ".gitignore",
        "QUICKSTART.md",
        "ASSISTANT_GUIDE.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "main.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
        else:
            print(f"✅ Найден: {file}")
    
    if missing_files:
        print(f"\n❌ Отсутствуют обязательные файлы: {missing_files}")
        return False
    
    # Проверяем структуру директорий
    print("\n📁 Проверка структуры директорий...")
    required_dirs = [
        "bot",
        "ai", 
        "database",
        "services",
        "utils",
        "admin"
    ]
    
    missing_dirs = []
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
        else:
            print(f"✅ Найдена директория: {dir_name}")
    
    if missing_dirs:
        print(f"\n❌ Отсутствуют директории: {missing_dirs}")
        return False
    
    # Проверяем базу знаний
    print("\n📚 Проверка базы знаний...")
    if os.path.exists("faq_ohs_ru_links.json"):
        size = os.path.getsize("faq_ohs_ru_links.json")
        print(f"✅ База знаний: {size:,} байт")
    else:
        print("❌ База знаний не найдена!")
        return False
    
    # Финальная проверка
    print("\n🎉 Подготовка завершена!")
    print("=" * 50)
    print("📋 Готовые файлы для GitHub:")
    
    # Подсчитываем размер
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk("."):
        # Пропускаем скрытые директории
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if not file.startswith('.'):
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    file_count += 1
    
    print(f"📊 Всего файлов: {file_count}")
    print(f"📊 Общий размер: {total_size:,} байт ({total_size/1024/1024:.1f} MB)")
    
    print("\n🚀 Проект готов к выгрузке на GitHub!")
    print("💡 Используйте: git add . && git commit -m 'Initial commit' && git push")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Подготовка успешно завершена!")
        else:
            print("\n❌ Подготовка завершена с ошибками!")
    except Exception as e:
        print(f"\n❌ Ошибка при подготовке: {e}")
