"""Репозитории пакетов с одинаковым набором операций.

Обход графа не знает, откуда взяты данные: из индекса Alpine Linux или
из тестового файла. Оба репозитория умеют:

    has(name)           есть ли такой пакет в репозитории;
    dependencies(name)  имена пакетов, от которых зависит пакет.
"""

from .apk import build_providers, direct_dependencies, load_index
from .testrepo import load_test_repository


class FileRepository:
    """Тестовый репозиторий, описанный словарём из файла."""

    def __init__(self, packages):
        """Создать репозиторий.

        :param packages: словарь имя пакета -> список его зависимостей.
        """
        self._packages = packages

    def has(self, name):
        """Проверить наличие пакета.

        :param name: имя пакета.
        :returns: True, если пакет описан в репозитории.
        """
        return name in self._packages

    def dependencies(self, name):
        """Получить зависимости пакета.

        :param name: имя пакета.
        :returns: список имён, для неописанного пакета он пуст.
        """
        return list(self._packages.get(name, ()))


class AlpineRepository:
    """Репозиторий Alpine Linux, построенный по индексу APKINDEX."""

    def __init__(self, index):
        """Создать репозиторий.

        :param index: разобранный индекс пакетов.
        """
        self._index = index
        self._providers = build_providers(index)

    def has(self, name):
        """Проверить наличие пакета.

        :param name: имя пакета.
        :returns: True, если пакет есть в индексе.
        """
        return name in self._index

    def dependencies(self, name):
        """Получить зависимости пакета в виде имён пакетов.

        Виртуальные имена заменяются на пакеты, которые их предоставляют.
        Зависимости без пакета и зависимость пакета от самого себя
        пропускаются, одинаковые пакеты записываются один раз.

        :param name: имя пакета.
        :returns: список имён пакетов.
        """
        result = []
        for dependency in direct_dependencies(
            self._index, name, self._providers
        ):
            target = dependency.package
            if target and target != name and target not in result:
                result.append(target)
        return result


def open_repository(config):
    """Открыть репозиторий в режиме, выбранном в конфигурации.

    :param config: проверенные параметры запуска.
    :returns: репозиторий с операциями has и dependencies.
    :raises RepositoryError: если данные не удалось получить.
    """
    if config.test_mode:
        return FileRepository(load_test_repository(config.repository))
    return AlpineRepository(load_index(config.repository))
