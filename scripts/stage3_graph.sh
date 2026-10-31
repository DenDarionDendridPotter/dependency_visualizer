#!/bin/sh
# Построение графа зависимостей: тестовые репозитории, ошибки, Alpine.
cd "$(dirname "$0")/.." || exit 1

show() {
    for file in "$@"; do
        echo
        echo "=== $file"
        ./run.sh --config "$file"
    done
}

echo "##### тестовый репозиторий: разные формы графа, глубина, фильтр"
show configs/stage3/tree_*.xml configs/stage3/diamond*.xml \
    configs/stage3/wide*.xml configs/stage3/chain_*.xml
echo
echo "##### тестовый репозиторий: циклические зависимости"
show configs/stage3/cycle*.xml configs/stage3/self_loop.xml \
    configs/stage3/two_cycles.xml
echo
echo "##### ошибки"
show configs/stage3/error_*.xml
echo
echo "##### настоящий репозиторий Alpine (нужен интернет)"
show configs/stage3/real_*.xml
