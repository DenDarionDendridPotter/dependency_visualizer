"""Тесты запуска программы из командной строки без доступа к сети."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.apk import parse_index
from src.errors import RepositoryError
from src.main import (
    EXIT_CONFIG_ERROR,
    EXIT_OK,
    EXIT_REPOSITORY_ERROR,
    main,
)

PROJECT = Path(__file__).resolve().parent.parent
CONFIG = str(PROJECT / "config.xml")
CONFIGS = PROJECT / "configs"
DEMO_DIRS = (CONFIGS / "stage3", CONFIGS / "stage4", CONFIGS / "stage5")
REAL_PREFIX = "real_"
ERROR_PREFIX = "error_"
INDEX = parse_index("P:curl\nV:1\nD:zlib\n\nP:zlib\nV:2\n")
TREE_HEADING = "ASCII-дерево"


def run(argv):
    """Запустить main и перехватить вывод.

    :param argv: аргументы командной строки.
    :returns: кортеж (код завершения, stdout, stderr).
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def run_with_package(config_path, old, new, index):
    """Запустить конфигурацию, подменив имя пакета и индекс Alpine.

    :param config_path: путь к конфигурации с настоящим репозиторием.
    :param old: подстрока, которую нужно заменить в конфигурации.
    :param new: подстрока-замена.
    :param index: индекс, который вернёт "скачивание".
    :returns: кортеж (код завершения, stdout, stderr).
    """
    text = config_path.read_text(encoding="utf-8").replace(old, new)
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / "config.xml"
        copy.write_text(text, encoding="utf-8")
        with mock.patch("src.repository.load_index", return_value=index):
            return run(["--config", str(copy)])


class MainTest(unittest.TestCase):
    """Проверки кода завершения и вывода программы."""

    def test_mermaid_for_alpine(self):
        """По скачанному индексу печатается диаграмма Mermaid."""
        with mock.patch("src.repository.load_index", return_value=INDEX):
            code, out, _ = run(["--config", CONFIG])
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(out.startswith("graph TD\n"))
        self.assertIn('n0["curl"]', out)
        self.assertIn("n0 --> n1", out)

    def test_ascii_tree_follows_config(self):
        """Дерево печатается, только если включён параметр ascii_tree."""
        with mock.patch("src.repository.load_index", return_value=INDEX):
            _, with_tree, _ = run(["--config", CONFIG])
        self.assertIn(TREE_HEADING, with_tree)
        self.assertIn("`-- zlib", with_tree)
        plain = CONFIGS / "stage3" / "tree_full.xml"
        self.assertNotIn(TREE_HEADING, run(["--config", str(plain)])[1])

    def test_filter_from_config_is_applied(self):
        """Фильтр из config.xml исключает пакеты с подстрокой."""
        index = parse_index("P:curl\nD:zlib dev-tools\n\nP:zlib\n\n"
                            "P:dev-tools\n")
        with mock.patch("src.repository.load_index", return_value=index):
            _, out, _ = run(["--config", CONFIG])
        self.assertIn('"zlib"', out)
        self.assertNotIn('"dev-tools"', out)

    def test_test_mode(self):
        """Тестовый режим работает без сети."""
        path = CONFIGS / "stage3" / "tree_full.xml"
        code, out, _ = run(["--config", str(path)])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("    n1 --> n3", out)

    def test_reverse_mode(self):
        """Режим обратных зависимостей включается параметром reverse."""
        path = CONFIGS / "stage4" / "reverse_tree.xml"
        code, out, _ = run(["--config", str(path)])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("обратные зависимости пакета D", out)
        self.assertIn("    n2 --> n1", out)

    def test_reverse_mode_for_alpine(self):
        """Обратные зависимости пакета Alpine берутся из индекса."""
        index = parse_index("P:a\nD:b\n\nP:b\n")
        path = CONFIGS / "stage4" / "real_reverse_curl.xml"
        code, out, _ = run_with_package(path, ">curl<", ">b<", index)
        self.assertEqual(code, EXIT_OK)
        self.assertIn('n1["a"]', out)
        self.assertIn("    n1 --> n0", out)

    def test_repository_error(self):
        """Ошибка репозитория печатается в stderr с кодом 2."""
        error = RepositoryError("нет связи")
        with mock.patch("src.repository.load_index", side_effect=error):
            code, out, err = run(["--config", CONFIG])
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка репозитория: нет связи", err)

    def test_config_error(self):
        """Ошибка конфигурации печатается в stderr с кодом 1."""
        path = CONFIGS / "errors" / "bad_url.xml"
        code, _, err = run(["--config", str(path)])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("ошибка конфигурации", err)

    def test_demo_configs_of_test_mode(self):
        """Все демонстрационные конфигурации тестового режима работают."""
        for directory in DEMO_DIRS:
            for path in sorted(directory.glob("*.xml")):
                if path.name.startswith(REAL_PREFIX):
                    continue
                expected = (EXIT_REPOSITORY_ERROR
                            if path.name.startswith(ERROR_PREFIX)
                            else EXIT_OK)
                with self.subTest(config=path.name):
                    code = run(["--config", str(path)])[0]
                    self.assertEqual(code, expected)


if __name__ == "__main__":
    unittest.main()
