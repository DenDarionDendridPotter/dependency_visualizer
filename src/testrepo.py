"""Тестовый репозиторий: граф зависимостей, записанный в текстовом файле.

Режим тестирования нужен, чтобы проверять алгоритмы на небольших
понятных графах без обращения к сети. Пакеты в таком файле называются
большими латинскими буквами. Формат файла, по одной строке на пакет:

    # всё после решётки считается комментарием
    A: B C      пакет A зависит от B и C
    B: D
    C: D
    D:          пакет D ни от чего не зависит

Зависимости можно разделять пробелами или запятыми. Если зависимость
не описана отдельной строкой, она считается пакетом без зависимостей.
"""

import re

from .errors import RepositoryError

COMMENT_MARK = "#"
NAME_SEPARATOR = ":"
LIST_SEPARATOR = ","
PACKAGE_NAME = re.compile(r"[A-Z]+")
TEXT_CHARSET = "utf-8"


def _unique(names):
    """Убрать повторы, сохранив порядок.

    :param names: список имён.
    :returns: список без повторов.
    """
    result = []
    for name in names:
        if name not in result:
            result.append(name)
    return result


def _parse_line(number, line):
    """Разобрать строку вида "A: B C".

    :param number: номер строки в файле для сообщений об ошибках.
    :param line: строка без комментария и пробелов по краям.
    :returns: кортеж (имя пакета, список зависимостей).
    :raises RepositoryError: если строка записана неверно.
    """
    name, separator, rest = line.partition(NAME_SEPARATOR)
    if not separator:
        raise RepositoryError(
            f"строка {number}: ожидалась запись вида A: B C, получено: {line}"
        )
    name = name.strip()
    dependencies = rest.replace(LIST_SEPARATOR, " ").split()
    for item in [name, *dependencies]:
        if not PACKAGE_NAME.fullmatch(item):
            raise RepositoryError(
                f"строка {number}: имя пакета должно состоять из больших "
                f"латинских букв, получено: {item!r}"
            )
    return name, _unique(dependencies)


def parse_test_repository(text):
    """Разобрать текст файла тестового репозитория.

    :param text: содержимое файла.
    :returns: словарь имя пакета -> список его зависимостей.
    :raises RepositoryError: при ошибке в записи или пустом файле.
    """
    packages = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split(COMMENT_MARK, 1)[0].strip()
        if not line:
            continue
        name, dependencies = _parse_line(number, line)
        if name in packages:
            raise RepositoryError(
                f"строка {number}: пакет {name} описан дважды"
            )
        packages[name] = dependencies
    if not packages:
        raise RepositoryError("тестовый репозиторий не содержит пакетов")
    return packages


def load_test_repository(path):
    """Прочитать и разобрать файл тестового репозитория.

    :param path: путь к файлу.
    :returns: словарь имя пакета -> список его зависимостей.
    :raises RepositoryError: если файл не прочитан или записан неверно.
    """
    try:
        with open(path, encoding=TEXT_CHARSET) as source:
            text = source.read()
    except (OSError, UnicodeDecodeError) as error:
        raise RepositoryError(
            f"не удалось прочитать тестовый репозиторий {path}: {error}"
        ) from error
    return parse_test_repository(text)
