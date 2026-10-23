#!/bin/sh
# Демонстрация обработки ошибок для всех параметров конфигурации.
cd "$(dirname "$0")/.." || exit 1

echo "=== корректная конфигурация config.xml"
./run.sh --config config.xml
echo
echo "=== файл конфигурации не существует"
./run.sh --config configs/no_such_config.xml
for file in configs/errors/*.xml; do
    echo
    echo "=== $file"
    ./run.sh --config "$file"
done
