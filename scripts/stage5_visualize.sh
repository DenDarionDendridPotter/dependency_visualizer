#!/bin/sh
# Описание графа на языке Mermaid и ASCII-дерево.
cd "$(dirname "$0")/.." || exit 1

show() {
    for file in "$@"; do
        echo
        echo "=== $file"
        ./run.sh --config "$file"
    done
}

echo "##### тестовый репозиторий: цикл, глубина, ромб, обратные зависимости"
show configs/stage5/test_*.xml
echo
echo "##### три пакета настоящего репозитория Alpine (нужен интернет)"
show configs/stage5/real_curl.xml configs/stage5/real_bash.xml \
    configs/stage5/real_git.xml configs/stage5/real_reverse_curl.xml
