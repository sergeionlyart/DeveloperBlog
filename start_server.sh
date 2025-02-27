#!/bin/bash

# Скрипт для запуска Gunicorn с оптимизированными настройками
# для предотвращения зависаний и проблем с сигналами winch

# Установка переменных среды для предотвращения проблем с сигналами
export GUNICORN_CMD_ARGS="--ignore-winch --preload --timeout 60 --workers 3 --log-level debug"

# Запуск Gunicorn с игнорированием сигнала winch
echo "Starting Gunicorn with optimized configuration..."
exec gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app