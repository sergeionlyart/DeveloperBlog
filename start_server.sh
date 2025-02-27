#!/bin/bash

# Скрипт для запуска Gunicorn с оптимизированными настройками
# для предотвращения зависаний и проблем с сигналами

# Функция для очистки при завершении
cleanup() {
    echo "Получен сигнал завершения. Выполняется корректное завершение..." 
    # Здесь можно добавить дополнительные команды очистки
    exit 0
}

# Регистрация обработчиков сигналов
trap cleanup SIGINT SIGTERM

# Установка переменных среды для оптимизации производительности
export GUNICORN_CMD_ARGS="--ignore-winch --preload --timeout 120 --workers 3 --max-requests 1000 --max-requests-jitter 200 --log-level info"

# Проверка наличия Python и Gunicorn
if ! command -v python3 &> /dev/null; then
    echo "Python не найден. Проверьте установку Python."
    exit 1
fi

if ! command -v gunicorn &> /dev/null; then
    echo "Gunicorn не найден. Проверьте установку Gunicorn."
    exit 1
fi

# Проверка наличия основных файлов приложения
if [ ! -f "main.py" ]; then
    echo "main.py не найден. Убедитесь, что вы находитесь в корректной директории."
    exit 1
fi

echo "Запуск Gunicorn с оптимизированной конфигурацией..."
echo "Используются настройки: $GUNICORN_CMD_ARGS"
echo "Сервер будет доступен по адресу: http://0.0.0.0:5000"

# Запуск Gunicorn с улучшенными параметрами
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app