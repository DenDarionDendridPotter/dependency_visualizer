"""Тесты вывода графа ASCII-деревом."""

import unittest

from src.graph import build_graph
from src.repository import FileRepository
from src.tree import format_tree
from tests.test_graph import CYCLE, DIAMOND, TREE, WIDE, repo

CHAIN_SIZE = 3000


def tree(text, root="A", depth=10, substring="", reverse=False):
    """Построить граф и получить строки дерева.

    :param text: содержимое тестового репозитория.
    :param root: анализируемый пакет.
    :param depth: максимальная глубина.
    :param substring: подстрока фильтра.
    :param reverse: True для обратных зависимостей.
    :returns: список строк вывода.
    """
    graph = build_graph(repo(text), root, depth, substring, reverse)
    return format_tree(graph).splitlines()


class TreeTest(unittest.TestCase):
    """Проверки рисунка дерева."""

    def test_simple_tree(self):
        """Простое дерево рисуется с отступами и значками ветвей."""
        self.assertEqual(tree(TREE), [
            "ASCII-дерево зависимостей пакета A:",
            "A",
            "|-- B",
            "|   |-- D",
            "|   `-- E",
            "`-- C",
            "    `-- F",
        ])

    def test_shared_dependency_is_not_expanded_twice(self):
        """Повторный пакет с зависимостями отмечен и не раскрывается."""
        self.assertEqual(tree(DIAMOND)[2:], [
            "|-- B",
            "|   `-- D",
            "|       `-- E",
            "`-- C",
            "    `-- D (см. выше)",
        ])

    def test_repeated_leaf_has_no_note(self):
        """Повторный пакет без зависимостей показывается без пометки."""
        lines = tree("A: B C\nB: D\nC: D\nD:\n")
        self.assertEqual(lines[-1], "    `-- D")

    def test_depth_one_is_marked(self):
        """Пакеты с нераскрытыми связями отмечены многоточием."""
        self.assertEqual(
            tree(TREE, depth=1)[1:], ["A", "|-- B ...", "`-- C ..."]
        )

    def test_cycle_is_marked(self):
        """Возврат в пакет на текущем пути отмечен как цикл."""
        self.assertEqual(tree(CYCLE)[2:], [
            "`-- B",
            "    `-- C",
            "        |-- A (цикл)",
            "        `-- D",
        ])

    def test_self_loop(self):
        """Зависимость пакета от себя отмечена как цикл."""
        self.assertEqual(tree("A: A B\nB:\n")[2:], [
            "|-- A (цикл)",
            "`-- B",
        ])

    def test_package_on_another_branch_is_not_a_cycle(self):
        """Пакет на соседней ветке это повтор, а не цикл."""
        lines = tree(WIDE)
        self.assertTrue(any(line.endswith("E (см. выше)") for line in lines))
        self.assertFalse(any("цикл" in line for line in lines))

    def test_single_package(self):
        """Пакет без зависимостей это одна строка."""
        self.assertEqual(tree("A:\n")[1:], ["A"])

    def test_filter_is_respected(self):
        """Исключённые фильтром пакеты в дереве не показываются."""
        text = "\n".join(tree(TREE, substring="C"))
        self.assertNotIn("C", text.split("\n", 1)[1])

    def test_reverse_heading_and_children(self):
        """В обратном режиме под пакетом идут зависящие от него."""
        self.assertEqual(tree(TREE, root="D", reverse=True), [
            "ASCII-дерево обратных зависимостей пакета D:",
            "D",
            "`-- B",
            "    `-- A",
        ])

    def test_long_chain_without_recursion(self):
        """Очень длинная цепочка рисуется без переполнения стека."""
        packages = {f"P{i}": [f"P{i + 1}"] for i in range(CHAIN_SIZE - 1)}
        packages[f"P{CHAIN_SIZE - 1}"] = []
        graph = build_graph(
            FileRepository(packages), "P0", CHAIN_SIZE
        )
        self.assertEqual(
            len(format_tree(graph).splitlines()), CHAIN_SIZE + 1
        )


if __name__ == "__main__":
    unittest.main()
