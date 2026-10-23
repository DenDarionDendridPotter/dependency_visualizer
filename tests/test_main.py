"""Тесты запуска программы из командной строки."""

import contextlib
import io
import unittest
from pathlib import Path

from src.main import EXIT_CONFIG_ERROR, EXIT_OK, main

PROJECT = Path(__file__).resolve().parent.parent


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

    def test_prints_all_parameters(self):
        """Корректная конфигурация выводит все параметры."""
        code, out, _ = run(["--config", str(PROJECT / "config.xml")])
        self.assertEqual(code, EXIT_OK)
        for key in ("package", "repository", "test_mode", "ascii_tree",
                    "max_depth", "filter"):
            self.assertIn(f"{key} = ", out)

    def test_error_goes_to_stderr(self):
        """Ошибка конфигурации печатается в stderr с кодом 1."""
        path = PROJECT / "configs" / "errors" / "bad_url.xml"
        code, out, err = run(["--config", str(path)])
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка конфигурации", err)


if __name__ == "__main__":
    unittest.main()
