#!/usr/bin/env bash
#
# Сделайте этот скрипт исполняемым командой: chmod +x export_to_md.sh
# Затем запустите его: ./export_to_md.sh

# Укажите корневую директорию вашего проекта
PROJECT_DIR="$(pwd)"

# Название выходного .md-файла
OUTPUT_FILE="project_bot_control_panel_legal.md"

############################################
# 1. Выводим структуру проекта (tree)
#    Исключаем venv, .venv, __pycache__, .git,
#    а также bin, lib, include, pyvenv.cfg
############################################
echo "# Project Structure" > "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
tree "$PROJECT_DIR" -I "venv|\.venv|__pycache__|\.git|bin|lib|include|pyvenv.cfg" >> "$OUTPUT_FILE"
echo '```' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

############################################
# 2. Заголовок для исходного кода
############################################
echo "# Source Code" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

############################################
# 3. Список файлов, которые хотим сохранить
############################################
files=(
  "app.py"
  "create_admin.py"
  "main.py"
  "migrate_db.py"
  "models.py"
  "reset_admin.py"
  "routes.py"
  "utils.py"
  "gunicorn_config.py"
  "start_server.sh"
)

############################################
# 4. Сохраняем каждый файл в общий Markdown
############################################
for file in "${files[@]}"; do
  # Проверяем, что файл существует в корне PROJECT_DIR (при необходимости подстройте путь)
  if [ -f "$PROJECT_DIR/$file" ]; then
    echo "## $file" >> "$OUTPUT_FILE"

    # Для .sh файлов используем синтаксис ```bash, для .py – ```python
    case "$file" in
      *.sh)
        echo '```bash' >> "$OUTPUT_FILE"
        cat "$PROJECT_DIR/$file" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
        ;;
      *.py)
        echo '```python' >> "$OUTPUT_FILE"
        cat "$PROJECT_DIR/$file" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
        ;;
      *)
        # На случай других расширений
        echo '```' >> "$OUTPUT_FILE"
        cat "$PROJECT_DIR/$file" >> "$OUTPUT_FILE"
        echo '```' >> "$OUTPUT_FILE"
        ;;
    esac

    echo "" >> "$OUTPUT_FILE"
  fi
done

echo "Done. Created $OUTPUT_FILE."