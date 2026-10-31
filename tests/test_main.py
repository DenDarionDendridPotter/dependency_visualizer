"""Тесты запуска программы из командной строки без доступа к сети."""

import contextlib
import io
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
DEMO_DIR = PROJECT / "configs" / "stage3"
REAL_PREFIX = "real_"
ERROR_PREFIX = "error_"
INDEX = parse_index("P:curl\nV:1\nD:zlib\n\nP:zlib\nV:2\n")


def run(argv):
    """Запустить main и перехватить вывод.

    :param argv: аргументы командной строки.
    :returns: кортеж (код завершения, stdout, stderr).
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class MainTest(unittest.TestCase):
    """Проверки кода завершения и вывода программы."""

    def test_prints_graph_for_alpine(self):
        """Граф пакета Alpine строится по скачанному индексу."""
        with mock.patch("src.repository.load_index", return_value=INDEX):
            code, out, _ = run(["--config", CONFIG])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("граф зависимостей пакета curl", out)
        self.assertIn("  curl -> zlib", out)

    def test_filter_from_config_is_applied(self):
        """Фильтр из config.xml исключает пакеты с подстрокой."""
        index = parse_index("P:curl\nD:zlib dev-tools\n\nP:zlib\n\n"
                            "P:dev-tools\n")
        with mock.patch("src.repository.load_index", return_value=index):
            _, out, _ = run(["--config", CONFIG])
        self.assertIn("curl -> zlib", out)
        self.assertNotIn("dev-tools", out.split("фильтр: dev)")[1])

    def test_test_mode(self):
        """Тестовый режим работает без сети."""
        path = DEMO_DIR / "tree_full.xml"
        code, out, _ = run(["--config", str(path)])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  B -> D", out)
        self.assertIn("пакетов: 6, зависимостей: 5", out)

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
        path = PROJECT / "configs" / "errors" / "bad_url.xml"
        code, _, err = run(["--config", str(path)])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("ошибка конфигурации", err)

    def test_demo_configs_of_test_mode(self):
        """Все демонстрационные конфигурации тестового режима работают."""
        for path in sorted(DEMO_DIR.glob("*.xml")):
            if path.name.startswith(REAL_PREFIX):
                continue
            expected = (EXIT_REPOSITORY_ERROR
                        if path.name.startswith(ERROR_PREFIX) else EXIT_OK)
            with self.subTest(config=path.name):
                self.assertEqual(run(["--config", str(path)])[0], expected)


if __name__ == "__main__":
    unittest.main()
