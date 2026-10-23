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

    def test_prints_direct_dependencies(self):
        """Выводятся прямые зависимости, параметры больше не печатаются."""
        with mock.patch("src.main.load_index", return_value=INDEX):
            code, out, _ = run(["--config", CONFIG])
        self.assertEqual(code, EXIT_OK)
        self.assertIn("zlib -> zlib", out)
        self.assertNotIn("max_depth = ", out)

    def test_repository_error(self):
        """Ошибка репозитория печатается в stderr с кодом 2."""
        error = RepositoryError("нет связи")
        with mock.patch("src.main.load_index", side_effect=error):
            code, out, err = run(["--config", CONFIG])
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка репозитория: нет связи", err)

    def test_config_error(self):
        """Ошибка конфигурации печатается в stderr с кодом 1."""
        path = PROJECT / "configs" / "errors" / "bad_url.xml"
        code, out, err = run(["--config", str(path)])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertIn("ошибка конфигурации", err)


if __name__ == "__main__":
    unittest.main()
