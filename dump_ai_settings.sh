#!/bin/bash

# Скрипт для создания дампа таблиц AI настроек

# Получаем путь к директории скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.py"

# Проверяем существование config.py
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Ошибка: Файл config.py не найден в $SCRIPT_DIR"
    exit 1
fi

# Извлекаем настройки базы данных из config.py
DB_NAME=$(grep -oP '"NAME":\s*os\.getenv\([^)]*,\s*"([^"]*)"' "$CONFIG_FILE" | sed -n 's/.*"\([^"]*\)"$/\1/p')
DB_USER=$(grep -oP '"USER":\s*os\.getenv\([^)]*,\s*"([^"]*)"' "$CONFIG_FILE" | sed -n 's/.*"\([^"]*\)"$/\1/p')
DB_PASSWORD=$(grep -oP '"PASSWORD":\s*os\.getenv\([^)]*,\s*"([^"]*)"' "$CONFIG_FILE" | sed -n 's/.*"\([^"]*\)"$/\1/p')
DB_HOST=$(grep -oP '"HOST":\s*os\.getenv\([^)]*,\s*"([^"]*)"' "$CONFIG_FILE" | sed -n 's/.*"\([^"]*\)"$/\1/p')
DB_PORT=$(grep -oP '"PORT":\s*os\.getenv\([^)]*,\s*"([^"]*)"' "$CONFIG_FILE" | sed -n 's/.*"\([^"]*\)"$/\1/p')

# Альтернативный метод извлечения - более надежный
if [ -z "$DB_NAME" ]; then
    DB_NAME=$(grep '"NAME"' "$CONFIG_FILE" | awk -F'"' '{print $4}')
fi
if [ -z "$DB_USER" ]; then
    DB_USER=$(grep '"USER"' "$CONFIG_FILE" | awk -F'"' '{print $4}')
fi
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(grep '"PASSWORD"' "$CONFIG_FILE" | awk -F'"' '{print $4}')
fi
if [ -z "$DB_HOST" ]; then
    DB_HOST=$(grep '"HOST"' "$CONFIG_FILE" | awk -F'"' '{print $4}')
fi
if [ -z "$DB_PORT" ]; then
    DB_PORT=$(grep '"PORT"' "$CONFIG_FILE" | awk -F'"' '{print $4}')
fi

# Проверяем, что все настройки извлечены
if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_HOST" ]; then
    echo "Ошибка: Не удалось извлечь все настройки базы данных из config.py"
    echo "DB_NAME: $DB_NAME"
    echo "DB_USER: $DB_USER"
    echo "DB_PASSWORD: $DB_PASSWORD"
    echo "DB_HOST: $DB_HOST"
    echo "DB_PORT: $DB_PORT"
    exit 1
fi

# Файл для дампа
DUMP_FILE="$SCRIPT_DIR/ai_settings.sql"

echo "Создание дампа таблиц AI настроек..."
echo "База данных: $DB_NAME@$DB_HOST:$DB_PORT"

# Используем mariadb-dump вместо устаревшего mysqldump
if command -v mariadb-dump &> /dev/null; then
    DUMP_CMD="mariadb-dump"
else
    DUMP_CMD="mysqldump"
    echo "Используется mysqldump (mariadb-dump не найден)"
fi

# Создаем дамп указанных таблиц
$DUMP_CMD -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" core_aimodelssettings core_systemprompts core_paymentgatewaysettings > "$DUMP_FILE"

# Проверяем успешность выполнения
if [ $? -eq 0 ]; then
    echo "Дамп успешно создан: $DUMP_FILE"
    echo "Размер файла: $(du -h "$DUMP_FILE" | cut -f1)"
else
    echo "Ошибка при создании дампа"
    exit 1
fi