"""Получение прямых зависимостей пакета из репозитория Alpine Linux.

Репозиторий apk хранит описание всех пакетов в архиве APKINDEX.tar.gz.
Внутри архива лежит текстовый файл APKINDEX: пакеты разделены пустой
строкой, каждая строка имеет вид "буква:значение". Нужные поля:

    P:curl                          имя пакета
    V:8.14.1-r2                     версия
    D:libcurl=8.14.1-r2 so:libz.so.1   зависимости через пробел
    p:cmd:curl=8.14.1-r2            что пакет предоставляет

Зависимость может быть именем пакета (libcurl), виртуальным именем
(so:libz.so.1 это библиотека, cmd:curl это команда) или конфликтом
(!имя). Виртуальное имя заменяется на пакет, который его
предоставляет. Менеджер пакетов apk и сторонние библиотеки не
используются: архив скачивается и разбирается стандартной
библиотекой Python.
"""

import io
import tarfile
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .errors import RepositoryError

INDEX_ARCHIVE = "APKINDEX.tar.gz"
INDEX_MEMBER = "APKINDEX"
ARCHIVE_SUFFIX = ".tar.gz"
URL_SEPARATOR = "/"
FIELD_SEPARATOR = ":"
NAME_FIELD = "P"
VERSION_FIELD = "V"
DEPENDS_FIELD = "D"
PROVIDES_FIELD = "p"
CONFLICT_PREFIX = "!"
VERSION_OPERATORS = "<>=~"
TEXT_CHARSET = "utf-8"
DOWNLOAD_TIMEOUT_SECONDS = 30


@dataclass
class PackageRecord:
    """Описание одного пакета из индекса репозитория.

    :param name: имя пакета.
    :param version: версия пакета.
    :param depends: зависимости в том виде, как они записаны в индексе.
    :param provides: виртуальные имена, которые предоставляет пакет.
    """

    name: str
    version: str = ""
    depends: list = field(default_factory=list)
    provides: list = field(default_factory=list)


@dataclass(frozen=True)
class Dependency:
    """Прямая зависимость пакета.

    :param raw: зависимость в том виде, как она записана в индексе.
    :param package: имя пакета, который её удовлетворяет, или None.
    """

    raw: str
    package: str | None


def index_url(repository):
    """Получить адрес архива индекса по адресу репозитория.

    :param repository: URL каталога репозитория или самого архива.
    :returns: URL файла APKINDEX.tar.gz.
    """
    if repository.endswith(ARCHIVE_SUFFIX):
        return repository
    return repository.rstrip(URL_SEPARATOR) + URL_SEPARATOR + INDEX_ARCHIVE


def download(url):
    """Скачать файл по URL.

    :param url: адрес файла.
    :returns: содержимое файла в виде байтов.
    :raises RepositoryError: если файл не удалось скачать.
    """
    try:
        with urllib.request.urlopen(
            url, timeout=DOWNLOAD_TIMEOUT_SECONDS
        ) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RepositoryError(
            f"сервер вернул ошибку {error.code} для {url}"
        ) from error
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise RepositoryError(f"не удалось скачать {url}: {error}") from error


def extract_index(archive):
    """Достать текст APKINDEX из архива APKINDEX.tar.gz.

    :param archive: содержимое архива в виде байтов.
    :returns: текст файла APKINDEX.
    :raises RepositoryError: если архив повреждён или файла в нём нет.
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            member = tar.extractfile(INDEX_MEMBER)
            data = member.read()
    except KeyError as error:
        raise RepositoryError(
            f"в архиве индекса нет файла {INDEX_MEMBER}"
        ) from error
    except (tarfile.TarError, OSError, EOFError) as error:
        raise RepositoryError(f"архив индекса повреждён: {error}") from error
    return data.decode(TEXT_CHARSET, errors="replace")


def _parse_block(block):
    """Разобрать описание одного пакета.

    :param block: строки одного пакета из APKINDEX.
    :returns: описание пакета или None, если в блоке нет имени.
    """
    fields = {}
    for line in block.splitlines():
        key, separator, value = line.partition(FIELD_SEPARATOR)
        if separator:
            fields[key] = value
    if NAME_FIELD not in fields:
        return None
    return PackageRecord(
        name=fields[NAME_FIELD],
        version=fields.get(VERSION_FIELD, ""),
        depends=fields.get(DEPENDS_FIELD, "").split(),
        provides=fields.get(PROVIDES_FIELD, "").split(),
    )


def parse_index(text):
    """Разобрать текст APKINDEX.

    :param text: содержимое файла APKINDEX.
    :returns: словарь имя пакета -> описание пакета.
    :raises RepositoryError: если в индексе нет ни одного пакета.
    """
    index = {}
    for block in text.split("\n\n"):
        record = _parse_block(block)
        if record is not None:
            index[record.name] = record
    if not index:
        raise RepositoryError("индекс репозитория не содержит пакетов")
    return index


def strip_version(token):
    """Убрать из зависимости ограничение версии.

    :param token: зависимость вида libcurl=8.14.1-r2 или so:libz.so.1.
    :returns: имя без версии: libcurl или so:libz.so.1.
    """
    for position, char in enumerate(token):
        if char in VERSION_OPERATORS:
            return token[:position]
    return token


def build_providers(index):
    """Составить таблицу: виртуальное имя -> пакет, который его даёт.

    :param index: разобранный индекс репозитория.
    :returns: словарь виртуальных имён.
    """
    providers = {}
    for record in index.values():
        for token in record.provides:
            providers.setdefault(strip_version(token), record.name)
    return providers


def direct_dependencies(index, package):
    """Найти прямые зависимости пакета.

    Конфликты (зависимости с !) пропускаются, виртуальные имена
    заменяются на пакеты, которые их предоставляют.

    :param index: разобранный индекс репозитория.
    :param package: имя пакета.
    :returns: список прямых зависимостей.
    :raises RepositoryError: если пакета нет в репозитории.
    """
    record = index.get(package)
    if record is None:
        raise RepositoryError(f"пакет {package} не найден в репозитории")
    providers = build_providers(index)
    result = []
    for token in record.depends:
        if token.startswith(CONFLICT_PREFIX):
            continue
        name = strip_version(token)
        provider = name if name in index else providers.get(name)
        result.append(Dependency(token, provider))
    return result


def load_index(repository):
    """Скачать и разобрать индекс репозитория.

    :param repository: URL каталога репозитория.
    :returns: разобранный индекс.
    :raises RepositoryError: при ошибке загрузки или разбора.
    """
    return parse_index(extract_index(download(index_url(repository))))


def unique_packages(dependencies):
    """Получить список различных пакетов из зависимостей.

    :param dependencies: прямые зависимости.
    :returns: имена пакетов без повторов, в порядке появления.
    """
    names = []
    for dependency in dependencies:
        if dependency.package and dependency.package not in names:
            names.append(dependency.package)
    return names


def format_dependencies(record, dependencies):
    """Собрать текст с прямыми зависимостями для вывода на экран.

    :param record: описание анализируемого пакета.
    :param dependencies: его прямые зависимости.
    :returns: многострочный текст.
    """
    lines = [f"прямые зависимости пакета {record.name} {record.version}:"]
    for dependency in dependencies:
        if dependency.package is None:
            target = "пакет не найден в репозитории"
        else:
            target = dependency.package
        lines.append(f"  {dependency.raw} -> {target}")
    if not dependencies:
        lines.append("  нет")
    packages = unique_packages(dependencies)
    total = f"итого пакетов: {len(packages)}"
    if packages:
        total += f" ({', '.join(packages)})"
    lines.append(total)
    return "\n".join(lines)
