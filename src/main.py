"""Точка входа инструмента визуализации графа зависимостей."""

import argparse
import sys

from src.config import load_config
from src.errors import ConfigError, RepositoryError
from src.graph import build_graph, find_cycles
from src.mermaid import to_mermaid
from src.repository import open_repository
from src.tree import format_tree

DEFAULT_CONFIG = "config.xml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 2


def parse_args(argv=None):
    """Разобрать аргументы командной строки.

    :param argv: список аргументов, по умолчанию sys.argv[1:].
    :returns: пространство имён с полем config.
    """
    parser = argparse.ArgumentParser(
        description="Визуализация графа зависимостей пакетов Alpine Linux"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help=f"путь к конфигурационному файлу XML (по умолчанию "
        f"{DEFAULT_CONFIG})",
    )
    return parser.parse_args(argv)


def show_graph(config):
    """Построить граф и вывести его описание на языке Mermaid.

    Если в конфигурации включён параметр ascii_tree, после диаграммы
    выводится ещё и ASCII-дерево.

    :param config: проверенные параметры.
    :raises RepositoryError: при ошибке данных или анализируемого пакета.
    """
    repository = open_repository(config)
    graph = build_graph(
        repository,
        config.package,
        config.max_depth,
        config.filter_substring,
        config.reverse,
    )
    print(to_mermaid(graph, find_cycles(graph)))
    if config.ascii_tree:
        print()
        print(format_tree(graph))


def main(argv=None):
    """Загрузить конфигурацию, построить граф и вывести его.

    :param argv: список аргументов командной строки.
    :returns: код завершения программы.
    """
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(f"ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        show_graph(config)
    except RepositoryError as error:
        print(f"ошибка репозитория: {error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
