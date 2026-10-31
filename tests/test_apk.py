"""Тесты разбора индекса репозитория Alpine Linux без доступа к сети."""

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from src.apk import (
    Dependency,
    build_providers,
    direct_dependencies,
    download,
    extract_index,
    index_url,
    parse_index,
    strip_version,
)
from src.errors import RepositoryError

SAMPLE_INDEX = """C:Q1abc=
P:curl
V:8.14.1-r2
D:libcurl=8.14.1-r2 so:libc.musl-x86_64.so.1 so:libz.so.1 !curl-old
p:cmd:curl=8.14.1-r2

P:libcurl
V:8.14.1-r2
D:so:libc.musl-x86_64.so.1
p:so:libcurl.so.4=4.8.0

P:musl
V:1.2.5-r0
p:so:libc.musl-x86_64.so.1=1

P:zlib
V:1.3.1-r1
D:so:libc.musl-x86_64.so.1
p:so:libz.so.1=1.3.1

P:broken
V:1.0
D:so:libmissing.so.1
"""

INDEX = parse_index(SAMPLE_INDEX)


def make_archive(members):
    """Собрать архив tar.gz в памяти.

    :param members: словарь имя файла -> текст.
    :returns: байты архива.
    """
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, text in members.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class ParseIndexTest(unittest.TestCase):
    """Проверки разбора текста APKINDEX."""

    def test_all_packages_found(self):
        """В индексе найдены все пакеты."""
        self.assertEqual(
            sorted(INDEX), ["broken", "curl", "libcurl", "musl", "zlib"]
        )

    def test_fields(self):
        """Имя, версия и зависимости читаются из своих полей."""
        curl = INDEX["curl"]
        self.assertEqual(curl.version, "8.14.1-r2")
        self.assertEqual(curl.depends[0], "libcurl=8.14.1-r2")
        self.assertEqual(curl.provides, ["cmd:curl=8.14.1-r2"])

    def test_package_without_depends(self):
        """У пакета без поля D список зависимостей пуст."""
        self.assertEqual(INDEX["musl"].depends, [])

    def test_empty_index(self):
        """Пустой индекс вызывает ошибку."""
        with self.assertRaises(RepositoryError):
            parse_index("\n\n")


class DependencyTest(unittest.TestCase):
    """Проверки поиска прямых зависимостей."""

    def test_strip_version(self):
        """Ограничение версии отрезается при любом операторе."""
        self.assertEqual(strip_version("libcurl=8.14.1-r2"), "libcurl")
        self.assertEqual(strip_version("libssl3>=3.3.0"), "libssl3")
        self.assertEqual(strip_version("a<2"), "a")
        self.assertEqual(strip_version("b~1.2"), "b")
        self.assertEqual(strip_version("so:libz.so.1"), "so:libz.so.1")

    def test_direct_dependencies(self):
        """Имена и виртуальные имена заменяются на пакеты."""
        result = direct_dependencies(INDEX, "curl")
        self.assertEqual(result, [
            Dependency("libcurl=8.14.1-r2", "libcurl"),
            Dependency("so:libc.musl-x86_64.so.1", "musl"),
            Dependency("so:libz.so.1", "zlib"),
        ])

    def test_conflicts_are_skipped(self):
        """Конфликт !curl-old не считается зависимостью."""
        raws = [d.raw for d in direct_dependencies(INDEX, "curl")]
        self.assertNotIn("!curl-old", raws)

    def test_unknown_virtual_name(self):
        """Виртуальное имя без поставщика остаётся без пакета."""
        result = direct_dependencies(INDEX, "broken")
        self.assertEqual(result, [Dependency("so:libmissing.so.1", None)])

    def test_missing_package(self):
        """Отсутствующий пакет вызывает ошибку."""
        with self.assertRaises(RepositoryError):
            direct_dependencies(INDEX, "nope")

    def test_prebuilt_providers(self):
        """Готовая таблица виртуальных имён даёт тот же результат."""
        providers = build_providers(INDEX)
        self.assertEqual(
            direct_dependencies(INDEX, "curl", providers),
            direct_dependencies(INDEX, "curl"),
        )

    def test_package_without_dependencies(self):
        """У пакета без поля D зависимостей нет."""
        self.assertEqual(direct_dependencies(INDEX, "musl"), [])


class ArchiveTest(unittest.TestCase):
    """Проверки адреса индекса, загрузки и распаковки архива."""

    def test_index_url(self):
        """К адресу каталога дописывается имя архива."""
        self.assertEqual(index_url("https://h/main/x86_64/"),
                         "https://h/main/x86_64/APKINDEX.tar.gz")
        self.assertEqual(index_url("https://h/APKINDEX.tar.gz"),
                         "https://h/APKINDEX.tar.gz")

    def test_extract_index(self):
        """Текст APKINDEX достаётся из архива."""
        archive = make_archive({"DESCRIPTION": "x", "APKINDEX": "P:a\n"})
        self.assertEqual(extract_index(archive), "P:a\n")

    def test_archive_without_index(self):
        """Архив без файла APKINDEX вызывает ошибку."""
        with self.assertRaises(RepositoryError):
            extract_index(make_archive({"DESCRIPTION": "x"}))

    def test_broken_archive(self):
        """Повреждённый архив вызывает ошибку."""
        with self.assertRaises(RepositoryError):
            extract_index(b"this is not a gzip archive")

    def test_download_local_file(self):
        """download читает файл по адресу file://."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "APKINDEX.tar.gz"
            path.write_bytes(b"data")
            self.assertEqual(download(path.as_uri()), b"data")

    def test_download_error(self):
        """Недоступный адрес вызывает ошибку."""
        with tempfile.TemporaryDirectory() as directory:
            url = (Path(directory) / "missing.tar.gz").as_uri()
            with self.assertRaises(RepositoryError):
                download(url)


if __name__ == "__main__":
    unittest.main()
