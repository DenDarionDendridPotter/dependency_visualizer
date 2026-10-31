"""Тесты загрузки и проверки конфигурационного файла XML."""

import tempfile
import unittest
from pathlib import Path

from src.config import Config, format_config, load_config
from src.errors import ConfigError

PROJECT = Path(__file__).resolve().parent.parent
ERRORS_DIR = PROJECT / "configs" / "errors"
URL = "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64"
EXPECTED_ERRORS = {
    "missing_package.xml": "<package>",
    "bad_package.xml": "недопустимое имя пакета",
    "missing_repository.xml": "<repository>",
    "bad_url.xml": "должен быть URL",
    "missing_test_file.xml": "тестового репозитория не найден",
    "bad_test_mode.xml": "<test_mode>",
    "bad_ascii_tree.xml": "<ascii_tree>",
    "bad_depth_text.xml": "целым числом",
    "bad_depth_zero.xml": "не меньше 1",
    "bad_filter.xml": "пробелы",
    "unknown_tag.xml": "неизвестный параметр",
    "wrong_root.xml": "корневым тегом",
    "broken.xml": "неверный формат XML",
    "duplicate_tag.xml": "задан дважды",
    "bad_reverse.xml": "<reverse>",
}


class ConfigTestCase(unittest.TestCase):
    """Общие помощники: временные каталоги и проверка ошибок."""

    def new_dir(self):
        """Создать временный каталог, удаляемый после теста.

        :returns: путь к новому каталогу.
        """
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return Path(directory.name)

    def write(self, inner):
        """Записать конфигурацию с заданным содержимым <config>.

        :param inner: XML внутри корневого тега.
        :returns: путь к созданному файлу.
        """
        path = self.new_dir() / "config.xml"
        path.write_text(f"<config>{inner}</config>", encoding="utf-8")
        return path

    def assert_error(self, path, fragment):
        """Проверить, что загрузка падает с нужным сообщением.

        :param path: путь к конфигурации.
        :param fragment: часть ожидаемого текста ошибки.
        """
        with self.assertRaises(ConfigError) as context:
            load_config(path)
        self.assertIn(fragment, str(context.exception))


class ValidConfigTest(ConfigTestCase):
    """Проверки корректных конфигураций."""

    def test_project_config(self):
        """Пример config.xml из проекта загружается со всеми параметрами."""
        config = load_config(PROJECT / "config.xml")
        self.assertEqual(
            config, Config("curl", URL, False, True, 3, "dev", False)
        )

    def test_defaults(self):
        """Необязательные параметры получают значения по умолчанию."""
        config = load_config(self.write(
            f"<package>bash</package><repository>{URL}</repository>"
        ))
        self.assertFalse(config.test_mode)
        self.assertFalse(config.ascii_tree)
        self.assertFalse(config.reverse)
        self.assertEqual(config.max_depth, 10)
        self.assertEqual(config.filter_substring, "")

    def test_reverse_true(self):
        """Значение true включает обратные зависимости."""
        path = self.write(
            f"<package>a</package><repository>{URL}</repository>"
            "<reverse>true</reverse>"
        )
        self.assertTrue(load_config(path).reverse)

    def test_test_mode_with_existing_file(self):
        """В тестовом режиме репозиторий это путь к существующему файлу."""
        repo = self.new_dir() / "repo.txt"
        repo.write_text("", encoding="utf-8")
        config = load_config(self.write(
            f"<package>A</package><repository>{repo}</repository>"
            "<test_mode>TRUE</test_mode>"
        ))
        self.assertTrue(config.test_mode)

    def test_format_key_value(self):
        """Все параметры выводятся строками ключ = значение."""
        text = format_config(load_config(PROJECT / "config.xml"))
        lines = text.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertIn("reverse = false", lines)
        self.assertIn("package = curl", lines)
        self.assertIn("ascii_tree = true", lines)
        self.assertIn("max_depth = 3", lines)


class ErrorConfigTest(ConfigTestCase):
    """Проверки сообщений об ошибках для каждого параметра."""

    def test_every_error_example(self):
        """Каждый пример из configs/errors даёт своё сообщение."""
        for name, fragment in EXPECTED_ERRORS.items():
            with self.subTest(file=name):
                self.assert_error(ERRORS_DIR / name, fragment)

    def test_all_examples_are_covered(self):
        """Для каждого файла с ошибкой есть ожидаемое сообщение."""
        names = {path.name for path in ERRORS_DIR.glob("*.xml")}
        self.assertEqual(names, set(EXPECTED_ERRORS))

    def test_missing_file(self):
        """Отсутствующий файл конфигурации вызывает ошибку."""
        self.assert_error(self.new_dir() / "nope.xml", "не найден")

    def test_negative_depth(self):
        """Отрицательная глубина вызывает ошибку."""
        path = self.write(
            f"<package>a</package><repository>{URL}</repository>"
            "<max_depth>-2</max_depth>"
        )
        self.assert_error(path, "не меньше 1")


if __name__ == "__main__":
    unittest.main()
