#!/bin/sh
# Вывод прямых зависимостей разных пакетов и ошибок загрузки.
cd "$(dirname "$0")/.." || exit 1

echo "=== config.xml (пакет curl)"
./run.sh --config config.xml
for file in configs/stage2/*.xml; do
    echo
    echo "=== $file"
    ./run.sh --config "$file"
done
