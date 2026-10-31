"""Тесты текстового отчёта о графе зависимостей."""

import unittest

from src.graph import build_graph, find_cycles
from src.report import format_cycles, format_graph, group_levels
from tests.test_graph import CYCLE, TREE, repo


def report(text, root="A", depth=10, substring=""):
    """Построить граф и собрать его отчёт.

    :param text: содержимое тестового репозитория.
    :param root: анализируемый пакет.
    :param depth: максимальная глубина.
    :param substring: подстрока фильтра.
    :returns: текст отчёта.
    """
    graph = build_graph(repo(text), root, depth, substring)
    return format_graph(graph, find_cycles(graph))


class ReportTest(unittest.TestCase):
    """Проверки вывода графа."""

    def test_group_levels(self):
        """Пакеты группируются по глубине."""
        graph = build_graph(repo(TREE), "A", 10)
        self.assertEqual(
            group_levels(graph),
            {0: ["A"], 1: ["B", "C"], 2: ["D", "E", "F"]},
        )

    def test_full_report(self):
        """Отчёт содержит заголовок, уровни, рёбра и итоги."""
        lines = report("A: B\nB:\n").splitlines()
        self.assertEqual(lines, [
            "граф зависимостей пакета A (глубина анализа: 10, фильтр: нет)",
            "уровень 0: A",
            "уровень 1: B",
            "зависимости:",
            "  A -> B",
            "пакетов: 2, зависимостей: 1",
            "циклические зависимости: нет",
        ])

    def test_filter_is_shown(self):
        """Фильтр указан в заголовке."""
        self.assertIn("фильтр: C", report(TREE, substring="C").splitlines()[0])

    def test_truncated_line(self):
        """Пакеты с нераскрытыми зависимостями перечислены."""
        text = report(TREE, depth=1)
        self.assertIn("не раскрыты из-за ограничения глубины у: B, C", text)

    def test_no_truncated_line_when_complete(self):
        """Если всё раскрыто, строки об ограничении нет."""
        self.assertNotIn("не раскрыты", report(TREE))

    def test_no_dependencies(self):
        """Пакет без зависимостей показан словом нет."""
        self.assertIn("  нет", report("A:\n"))

    def test_cycles_in_report(self):
        """Циклы перечислены стрелками."""
        text = report(CYCLE)
        self.assertIn("циклические зависимости (1):", text)
        self.assertIn("  A -> B -> C -> A", text)

    def test_format_cycles_empty(self):
        """Без циклов выводится одна строка."""
        self.assertEqual(format_cycles([]), ["циклические зависимости: нет"])


if __name__ == "__main__":
    unittest.main()
