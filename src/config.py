"""Загрузка и проверка параметров из конфигурационного файла XML.

Пример файла:

    <config>
      <package>curl</package>
      <repository>https://example.org/alpine/main/x86_64</repository>
      <test_mode>false</test_mode>
      <ascii_tree>true</ascii_tree>
      <max_depth>3</max_depth>
      <filter>dev</filter>
    </config>
"""

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from .errors import ConfigError

ROOT_TAG = "config"
PACKAGE_TAG = "package"
REPOSITORY_TAG = "repository"
TEST_MODE_TAG = "test_mode"
ASCII_TREE_TAG = "ascii_tree"
MAX_DEPTH_TAG = "max_depth"
FILTER_TAG = "filter"
KNOWN_TAGS = (
    PACKAGE_TAG,
    REPOSITORY_TAG,
    TEST_MODE_TAG,
    ASCII_TREE_TAG,
    MAX_DEPTH_TAG,
    FILTER_TAG,
)
REQUIRED_TAGS = (PACKAGE_TAG, REPOSITORY_TAG)
TRUE_TEXT = "true"
FALSE_TEXT = "false"
DEFAULT_MAX_DEPTH = 10
MIN_DEPTH = 1
URL_PREFIXES = ("http://", "https://")
PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


@dataclass(frozen=True)
class Config:
    """Параметры, заданные пользователем в конфигурационном файле.

    :param package: имя анализируемого пакета.
    :param repository: URL репозитория или путь к тестовому файлу.
    :param test_mode: True, если repository это путь к тестовому файлу.
    :param ascii_tree: True, если зависимости выводятся ASCII-деревом.
    :param max_depth: максимальная глубина анализа зависимостей.
    :param filter_substring: пакеты с этой подстрокой не учитываются.
    """

    package: str
    repository: str
    test_mode: bool = False
    ascii_tree: bool = False
    max_depth: int = DEFAULT_MAX_DEPTH
    filter_substring: str = ""

    def items(self):
        """Вернуть параметры в виде пар (ключ, значение).

        :returns: список пар в порядке тегов конфигурационного файла.
        """
        return [
            (PACKAGE_TAG, self.package),
            (REPOSITORY_TAG, self.repository),
            (TEST_MODE_TAG, _bool_text(self.test_mode)),
            (ASCII_TREE_TAG, _bool_text(self.ascii_tree)),
            (MAX_DEPTH_TAG, str(self.max_depth)),
            (FILTER_TAG, self.filter_substring),
        ]


def _bool_text(value):
    """Записать логическое значение так же, как в файле.

    :param value: логическое значение.
    :returns: строка true или false.
    """
    return TRUE_TEXT if value else FALSE_TEXT


def _read_root(path):
    """Прочитать XML-файл и вернуть его корневой элемент.

    :param path: путь к конфигурационному файлу.
    :returns: корневой элемент XML.
    :raises ConfigError: если файла нет или формат неверен.
    """
    try:
        root = ElementTree.parse(path).getroot()
    except FileNotFoundError as error:
        raise ConfigError(f"файл конфигурации не найден: {path}") from error
    except ElementTree.ParseError as error:
        raise ConfigError(f"неверный формат XML в {path}: {error}") from error
    except OSError as error:
        raise ConfigError(f"не удалось прочитать {path}: {error}") from error
    if root.tag != ROOT_TAG:
        raise ConfigError(
            f"корневым тегом должен быть <{ROOT_TAG}>, найден <{root.tag}>"
        )
    return root


def _collect_values(root):
    """Собрать текст всех параметров из корневого элемента.

    :param root: корневой элемент <config>.
    :returns: словарь тег -> текст без пробелов по краям.
    :raises ConfigError: при неизвестном или повторном теге.
    """
    values = {}
    for element in root:
        if element.tag not in KNOWN_TAGS:
            raise ConfigError(f"неизвестный параметр: <{element.tag}>")
        if element.tag in values:
            raise ConfigError(f"параметр <{element.tag}> задан дважды")
        values[element.tag] = (element.text or "").strip()
    for tag in REQUIRED_TAGS:
        if not values.get(tag):
            raise ConfigError(f"не задан обязательный параметр <{tag}>")
    return values


def _parse_bool(tag, text):
    """Разобрать логический параметр.

    :param tag: имя параметра для сообщения об ошибке.
    :param text: значение из файла, пустое означает false.
    :returns: логическое значение.
    :raises ConfigError: если значение не true и не false.
    """
    lowered = text.lower()
    if lowered in ("", FALSE_TEXT):
        return False
    if lowered == TRUE_TEXT:
        return True
    raise ConfigError(
        f"параметр <{tag}> должен быть {TRUE_TEXT} или {FALSE_TEXT}, "
        f"получено: {text}"
    )


def _parse_depth(text):
    """Разобрать максимальную глубину анализа.

    :param text: значение из файла, пустое означает глубину по умолчанию.
    :returns: целое положительное число.
    :raises ConfigError: если значение не целое или меньше минимума.
    """
    if not text:
        return DEFAULT_MAX_DEPTH
    try:
        depth = int(text)
    except ValueError as error:
        raise ConfigError(
            f"параметр <{MAX_DEPTH_TAG}> должен быть целым числом, "
            f"получено: {text}"
        ) from error
    if depth < MIN_DEPTH:
        raise ConfigError(
            f"параметр <{MAX_DEPTH_TAG}> должен быть не меньше {MIN_DEPTH}"
        )
    return depth


def _check_package(name):
    """Проверить имя анализируемого пакета.

    :param name: имя пакета из файла.
    :raises ConfigError: если имя содержит недопустимые символы.
    """
    if not PACKAGE_NAME.fullmatch(name):
        raise ConfigError(f"недопустимое имя пакета: {name}")


def _check_repository(repository, test_mode):
    """Проверить адрес репозитория с учётом режима работы.

    :param repository: URL или путь к тестовому файлу.
    :param test_mode: True для тестового режима.
    :raises ConfigError: если адрес не подходит для выбранного режима.
    """
    if not test_mode:
        if not repository.startswith(URL_PREFIXES):
            raise ConfigError(
                "в обычном режиме репозиторий должен быть URL, "
                f"начинающимся с http:// или https://, получено: {repository}"
            )
        return
    if not Path(repository).is_file():
        raise ConfigError(f"файл тестового репозитория не найден: {repository}")


def _check_filter(substring):
    """Проверить подстроку для фильтрации пакетов.

    :param substring: подстрока из файла, может быть пустой.
    :raises ConfigError: если подстрока содержит пробельные символы.
    """
    if any(char.isspace() for char in substring):
        raise ConfigError(
            f"подстрока фильтра не может содержать пробелы: {substring!r}"
        )


def load_config(path):
    """Загрузить и проверить конфигурацию.

    :param path: путь к конфигурационному файлу XML.
    :returns: проверенные параметры.
    :raises ConfigError: при любой ошибке файла или параметра.
    """
    values = _collect_values(_read_root(path))
    test_mode = _parse_bool(TEST_MODE_TAG, values.get(TEST_MODE_TAG, ""))
    config = Config(
        package=values[PACKAGE_TAG],
        repository=values[REPOSITORY_TAG],
        test_mode=test_mode,
        ascii_tree=_parse_bool(ASCII_TREE_TAG, values.get(ASCII_TREE_TAG, "")),
        max_depth=_parse_depth(values.get(MAX_DEPTH_TAG, "")),
        filter_substring=values.get(FILTER_TAG, ""),
    )
    _check_package(config.package)
    _check_repository(config.repository, config.test_mode)
    _check_filter(config.filter_substring)
    return config


def format_config(config):
    """Собрать текст со всеми параметрами в формате ключ = значение.

    :param config: проверенные параметры.
    :returns: многострочный текст, по одному параметру в строке.
    """
    return "\n".join(f"{key} = {value}" for key, value in config.items())
