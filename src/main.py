"""Точка входа инструмента визуализации графа зависимостей."""

import argparse
import sys

from src.config import format_config, load_config
from src.errors import ConfigError

DEFAULT_CONFIG = "config.xml"
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1


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


def main(argv=None):
    """Загрузить конфигурацию и вывести все параметры.

    :param argv: список аргументов командной строки.
    :returns: код завершения программы.
    """
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(f"ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    print(format_config(config))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
