#!/bin/sh
# Обратные зависимости: кто зависит от пакета.
cd "$(dirname "$0")/.." || exit 1

show() {
    for file in "$@"; do
        echo
        echo "=== $file"
        ./run.sh --config "$file"
    done
}

echo "##### тестовый репозиторий: обратные зависимости"
show configs/stage4/reverse_*.xml
echo
echo "##### ошибки"
show configs/stage4/error_*.xml configs/errors/bad_reverse.xml
echo
echo "##### настоящий репозиторий Alpine (нужен интернет)"
show configs/stage4/real_*.xml
