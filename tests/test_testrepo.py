"""Тесты разбора файла тестового репозитория."""

import unittest
from pathlib import Path

from src.errors import RepositoryError
from src.testrepo import load_test_repository, parse_test_repository

PROJECT = Path(__file__).resolve().parent.parent
BAD_DIR = PROJECT / "repos" / "errors"
EXPECTED_ERRORS = {
    "bad_name.txt": "больших латинских букв",
    "no_colon.txt": "ожидалась запись",
    "duplicate.txt": "описан дважды",
    "empty.txt": "не содержит пакетов",
    "digits.txt": "больших латинских букв",
}


class ParseTest(unittest.TestCase):
    """Проверки разбора текста репозитория."""

    def test_simple_graph(self):
        """Зависимости читаются в том порядке, как записаны."""
        packages = parse_test_repository("A: B C\nB:\nC: B\n")
        self.assertEqual(packages, {"A": ["B", "C"], "B": [], "C": ["B"]})

    def test_comments_and_blank_lines(self):
        """Комментарии и пустые строки пропускаются."""
        text = "# заголовок\n\nA: B  # зависит от B\nB:\n"
        self.assertEqual(parse_test_repository(text), {"A": ["B"], "B": []})

    def test_commas_and_spaces(self):
        """Зависимости можно разделять запятыми и пробелами."""
        packages = parse_test_repository("A: B,C ,D\n")
        self.assertEqual(packages["A"], ["B", "C", "D"])

    def test_repeated_dependency(self):
        """Повторная зависимость записывается один раз."""
        self.assertEqual(parse_test_repository("A: B B\n")["A"], ["B"])

    def test_multi_letter_names(self):
        """Имя может состоять из нескольких больших букв."""
        self.assertEqual(parse_test_repository("AB: CD\n")["AB"], ["CD"])

    def test_undefined_dependency_is_allowed(self):
        """Зависимость без своей строки допустима."""
        self.assertEqual(parse_test_repository("A: Z\n"), {"A": ["Z"]})


class ErrorTest(unittest.TestCase):
    """Проверки сообщений об ошибках."""

    def test_every_bad_file(self):
        """Каждый пример из repos/errors даёт своё сообщение."""
        for name, fragment in EXPECTED_ERRORS.items():
            with self.subTest(file=name):
                with self.assertRaises(RepositoryError) as context:
                    load_test_repository(BAD_DIR / name)
                self.assertIn(fragment, str(context.exception))

    def test_all_bad_files_are_covered(self):
        """Для каждого файла с ошибкой есть ожидаемое сообщение."""
        names = {path.name for path in BAD_DIR.glob("*.txt")}
        self.assertEqual(names, set(EXPECTED_ERRORS))

    def test_error_mentions_line_number(self):
        """Сообщение указывает номер строки с ошибкой."""
        with self.assertRaises(RepositoryError) as context:
            parse_test_repository("A: B\nB: c\n")
        self.assertIn("строка 2", str(context.exception))

    def test_missing_file(self):
        """Отсутствующий файл вызывает ошибку."""
        with self.assertRaises(RepositoryError):
            load_test_repository(PROJECT / "repos" / "no_such_file.txt")

    def test_project_repositories_are_valid(self):
        """Все примеры репозиториев проекта читаются без ошибок."""
        for path in (PROJECT / "repos").glob("*.txt"):
            with self.subTest(file=path.name):
                self.assertTrue(load_test_repository(path))


if __name__ == "__main__":
    unittest.main()
