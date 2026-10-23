"""Точка входа инструмента визуализации графа зависимостей."""

import argparse
import sys

from src.apk import direct_dependencies, format_dependencies, load_index
from src.config import load_config
from src.errors import ConfigError, RepositoryError

DEFAULT_CONFIG = "config.xml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 2
TEST_MODE_NOTE = (
    "режим тестового репозитория будет поддержан на этапе 3, "
    "сейчас укажите URL реального репозитория"
)


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


def show_direct_dependencies(config):
    """Скачать индекс репозитория и вывести прямые зависимости пакета.

    :param config: проверенные параметры.
    :raises RepositoryError: при ошибке загрузки или если пакета нет.
    """
    if config.test_mode:
        raise RepositoryError(TEST_MODE_NOTE)
    index = load_index(config.repository)
    dependencies = direct_dependencies(index, config.package)
    print(format_dependencies(index[config.package], dependencies))


def main(argv=None):
    """Загрузить конфигурацию и вывести прямые зависимости пакета.

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
        show_direct_dependencies(config)
    except RepositoryError as error:
        print(f"ошибка репозитория: {error}", file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
