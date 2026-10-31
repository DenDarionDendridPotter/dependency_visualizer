"""Тесты репозиториев: тестового файла и индекса Alpine Linux."""

import unittest
from pathlib import Path
from unittest import mock

from src.apk import parse_index
from src.config import Config
from src.repository import AlpineRepository, FileRepository, open_repository
from tests.test_apk import SAMPLE_INDEX

PROJECT = Path(__file__).resolve().parent.parent
SELF_PROVIDER = "P:a\nD:so:x\np:so:x\n\nP:b\nD:a so:x a\n"


class FileRepositoryTest(unittest.TestCase):
    """Проверки тестового репозитория."""

    def test_has(self):
        """Описанный пакет найден, неописанный нет."""
        repository = FileRepository({"A": []})
        self.assertTrue(repository.has("A"))
        self.assertFalse(repository.has("B"))

    def test_dependencies_are_copied(self):
        """Изменение результата не портит репозиторий."""
        repository = FileRepository({"A": ["B"]})
        repository.dependencies("A").append("C")
        self.assertEqual(repository.dependencies("A"), ["B"])

    def test_undefined_package_has_no_dependencies(self):
        """У неописанного пакета зависимостей нет."""
        self.assertEqual(FileRepository({}).dependencies("Z"), [])


class AlpineRepositoryTest(unittest.TestCase):
    """Проверки репозитория по индексу APKINDEX."""

    def test_has(self):
        """Пакеты индекса находятся."""
        repository = AlpineRepository(parse_index(SAMPLE_INDEX))
        self.assertTrue(repository.has("curl"))
        self.assertFalse(repository.has("so:libz.so.1"))

    def test_dependencies_are_package_names(self):
        """Версии и виртуальные имена заменяются именами пакетов."""
        repository = AlpineRepository(parse_index(SAMPLE_INDEX))
        self.assertEqual(
            repository.dependencies("curl"), ["libcurl", "musl", "zlib"]
        )

    def test_unresolved_dependency_is_skipped(self):
        """Зависимость без пакета в результат не попадает."""
        repository = AlpineRepository(parse_index(SAMPLE_INDEX))
        self.assertEqual(repository.dependencies("broken"), [])

    def test_self_dependency_and_repeats_are_skipped(self):
        """Зависимость от себя и повторы не попадают в результат."""
        repository = AlpineRepository(parse_index(SELF_PROVIDER))
        self.assertEqual(repository.dependencies("a"), [])
        self.assertEqual(repository.dependencies("b"), ["a"])


class OpenRepositoryTest(unittest.TestCase):
    """Проверки выбора репозитория по конфигурации."""

    def test_test_mode_reads_file(self):
        """В тестовом режиме данные читаются из файла."""
        config = Config("A", str(PROJECT / "repos" / "tree.txt"), True)
        repository = open_repository(config)
        self.assertIsInstance(repository, FileRepository)
        self.assertEqual(repository.dependencies("A"), ["B", "C"])

    def test_normal_mode_downloads_index(self):
        """В обычном режиме скачивается индекс."""
        config = Config("curl", "https://example.org/main/x86_64")
        index = parse_index(SAMPLE_INDEX)
        with mock.patch("src.repository.load_index", return_value=index) as m:
            repository = open_repository(config)
        m.assert_called_once_with("https://example.org/main/x86_64")
        self.assertIsInstance(repository, AlpineRepository)


if __name__ == "__main__":
    unittest.main()
