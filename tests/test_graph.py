"""Тесты обхода графа в ширину и поиска циклов."""

import unittest

from src.errors import RepositoryError
from src.graph import build_graph, find_cycles, is_excluded
from src.repository import FileRepository
from src.testrepo import parse_test_repository

TREE = "A: B C\nB: D E\nC: F\nD:\nE:\nF:\n"
DIAMOND = "A: B C\nB: D\nC: D\nD: E\nE:\n"
WIDE = "A: B C\nB: E\nC: D\nD: E F\nE: G\nF:\nG:\n"
CYCLE = "A: B\nB: C\nC: A D\nD:\n"
TWO_CYCLES = "A: B C\nB: A\nC: D\nD: C\n"
LONG_CHAIN_SIZE = 5000


def repo(text):
    """Создать тестовый репозиторий из текста.

    :param text: содержимое файла тестового репозитория.
    :returns: репозиторий для построения графа.
    """
    return FileRepository(parse_test_repository(text))


def chain_repository(size):
    """Создать репозиторий-цепочку P0 -> P1 -> ... -> P(size-1).

    :param size: число пакетов.
    :returns: репозиторий с одной длинной цепочкой.
    """
    packages = {f"P{i}": [f"P{i + 1}"] for i in range(size - 1)}
    packages[f"P{size - 1}"] = []
    return FileRepository(packages)


class BuildGraphTest(unittest.TestCase):
    """Проверки построения графа."""

    def test_breadth_first_order(self):
        """Пакеты перечисляются по уровням, слева направо."""
        graph = build_graph(repo(TREE), "A", 10)
        self.assertEqual(list(graph.levels), ["A", "B", "C", "D", "E", "F"])
        self.assertEqual(
            list(graph.levels.values()), [0, 1, 1, 2, 2, 2]
        )

    def test_edges(self):
        """Рёбра графа совпадают с зависимостями в файле."""
        graph = build_graph(repo(TREE), "A", 10)
        self.assertEqual(graph.edges(), [
            ("A", "B"), ("A", "C"), ("B", "D"), ("B", "E"), ("C", "F"),
        ])

    def test_depth_limit(self):
        """Глубина 1 даёт корень и прямые зависимости."""
        graph = build_graph(repo(TREE), "A", 1)
        self.assertEqual(list(graph.levels), ["A", "B", "C"])
        self.assertEqual(graph.truncated, {"B", "C"})

    def test_depth_limit_leaf_is_not_truncated(self):
        """Пакет без зависимостей на предельной глубине не обрезан."""
        graph = build_graph(repo(TREE), "A", 2)
        self.assertEqual(graph.truncated, set())

    def test_shared_dependency_once(self):
        """Общая зависимость попадает в граф один раз."""
        graph = build_graph(repo(DIAMOND), "A", 10)
        self.assertEqual(list(graph.levels).count("D"), 1)
        self.assertEqual(graph.edges().count(("B", "D")), 1)
        self.assertIn(("C", "D"), graph.edges())

    def test_shortest_depth_wins(self):
        """Пакет получает наименьшую из глубин, на которых он найден."""
        graph = build_graph(repo(WIDE), "A", 10)
        self.assertEqual(graph.levels["E"], 2)

    def test_unlimited_depth_reaches_everything(self):
        """Большая глубина раскрывает граф целиком."""
        graph = build_graph(repo(WIDE), "A", 100)
        self.assertEqual(set(graph.levels), set("ABCDEFG"))

    def test_only_reachable_packages(self):
        """Пакеты, до которых нет пути от корня, не попадают в граф."""
        graph = build_graph(repo(TREE), "C", 10)
        self.assertEqual(list(graph.levels), ["C", "F"])

    def test_undefined_dependency_is_leaf(self):
        """Неописанная зависимость становится пакетом без зависимостей."""
        graph = build_graph(repo("A: Z\n"), "A", 10)
        self.assertEqual(graph.edges(), [("A", "Z")])

    def test_long_chain_without_recursion(self):
        """Цепочка в тысячи пакетов обходится без переполнения стека."""
        graph = build_graph(
            chain_repository(LONG_CHAIN_SIZE), "P0", LONG_CHAIN_SIZE
        )
        self.assertEqual(len(graph.levels), LONG_CHAIN_SIZE)
        self.assertEqual(find_cycles(graph), [])


class FilterTest(unittest.TestCase):
    """Проверки исключения пакетов по подстроке."""

    def test_is_excluded(self):
        """Пустая подстрока ничего не исключает."""
        self.assertFalse(is_excluded("curl", ""))
        self.assertTrue(is_excluded("libcurl", "curl"))
        self.assertFalse(is_excluded("zlib", "curl"))

    def test_filter_cuts_branch(self):
        """Исключённый пакет и недоступное без него пропадают."""
        graph = build_graph(repo(TREE), "A", 10, "C")
        self.assertEqual(list(graph.levels), ["A", "B", "D", "E"])
        self.assertNotIn(("A", "C"), graph.edges())

    def test_filter_keeps_other_paths(self):
        """Пакет остаётся, если до него есть другой путь."""
        graph = build_graph(repo(DIAMOND), "A", 10, "B")
        self.assertIn("D", graph.levels)
        self.assertNotIn("B", graph.levels)

    def test_filter_is_case_sensitive(self):
        """Подстрока сравнивается с учётом регистра."""
        graph = build_graph(repo(TREE), "A", 10, "c")
        self.assertEqual(len(graph.levels), 6)

    def test_root_excluded_by_filter(self):
        """Корень с подстрокой фильтра вызывает ошибку."""
        with self.assertRaises(RepositoryError) as context:
            build_graph(repo(TREE), "A", 10, "A")
        self.assertIn("исключён фильтром", str(context.exception))

    def test_missing_root(self):
        """Пакета нет в репозитории: ошибка."""
        with self.assertRaises(RepositoryError) as context:
            build_graph(repo(TREE), "Z", 10)
        self.assertIn("не найден", str(context.exception))


class CycleTest(unittest.TestCase):
    """Проверки циклических зависимостей."""

    def test_no_cycles(self):
        """В графе без циклов их нет."""
        self.assertEqual(find_cycles(build_graph(repo(DIAMOND), "A", 10)), [])

    def test_simple_cycle(self):
        """Цикл A -> B -> C -> A находится, обход завершается."""
        graph = build_graph(repo(CYCLE), "A", 10)
        self.assertEqual(find_cycles(graph), [["A", "B", "C", "A"]])
        self.assertEqual(set(graph.levels), set("ABCD"))

    def test_self_loop(self):
        """Зависимость пакета от самого себя это цикл."""
        graph = build_graph(repo("A: A B\nB:\n"), "A", 10)
        self.assertEqual(find_cycles(graph), [["A", "A"]])

    def test_two_cycles(self):
        """Два независимых цикла находятся оба."""
        graph = build_graph(repo(TWO_CYCLES), "A", 10)
        self.assertEqual(
            sorted(find_cycles(graph)), [["A", "B", "A"], ["C", "D", "C"]]
        )

    def test_cycle_hidden_by_depth(self):
        """Если цикл не раскрыт из-за глубины, он не находится."""
        graph = build_graph(repo(CYCLE), "A", 2)
        self.assertEqual(find_cycles(graph), [])
        self.assertEqual(graph.truncated, {"C"})

    def test_cycle_not_through_root(self):
        """Цикл ниже корня находится тоже."""
        graph = build_graph(repo("A: B\nB: C\nC: B\n"), "A", 10)
        self.assertEqual(find_cycles(graph), [["B", "C", "B"]])


class ReverseTest(unittest.TestCase):
    """Проверки обратных зависимостей: кто зависит от пакета."""

    def test_reverse_levels(self):
        """От D зависит B, от B зависит A."""
        graph = build_graph(repo(TREE), "D", 10, reverse=True)
        self.assertEqual(list(graph.levels), ["D", "B", "A"])

    def test_reverse_edges_point_from_dependent(self):
        """Рёбра по-прежнему идут от зависящего к зависимости."""
        graph = build_graph(repo(TREE), "D", 10, reverse=True)
        self.assertEqual(graph.edges(), [("B", "D"), ("A", "B")])

    def test_reverse_same_edges_as_forward_subgraph(self):
        """Каждое ребро обратного графа есть и в прямом графе."""
        forward = set(build_graph(repo(DIAMOND), "A", 10).edges())
        backward = build_graph(repo(DIAMOND), "E", 10, reverse=True).edges()
        self.assertTrue(set(backward) <= forward)

    def test_reverse_diamond(self):
        """В ромбе от E зависят D, затем B и C, затем A."""
        graph = build_graph(repo(DIAMOND), "E", 10, reverse=True)
        self.assertEqual(list(graph.levels), ["E", "D", "B", "C", "A"])
        self.assertEqual(graph.levels["A"], 3)

    def test_reverse_depth_limit(self):
        """Глубина ограничивает и обратный обход."""
        graph = build_graph(repo(TREE), "D", 1, reverse=True)
        self.assertEqual(list(graph.levels), ["D", "B"])
        self.assertEqual(graph.truncated, {"B"})

    def test_reverse_filter(self):
        """Фильтр исключает пакеты и из обратного обхода."""
        graph = build_graph(repo(DIAMOND), "E", 10, "B", reverse=True)
        self.assertEqual(list(graph.levels), ["E", "D", "C", "A"])

    def test_reverse_of_top_package(self):
        """От корня дерева никто не зависит."""
        graph = build_graph(repo(TREE), "A", 10, reverse=True)
        self.assertEqual(list(graph.levels), ["A"])
        self.assertEqual(graph.edges(), [])

    def test_reverse_cycle_is_written_by_dependency(self):
        """Цикл записан по направлению зависимостей, как в прямом обходе."""
        graph = build_graph(repo(CYCLE), "A", 10, reverse=True)
        self.assertEqual(find_cycles(graph), [["A", "B", "C", "A"]])

    def test_reverse_self_loop(self):
        """Пакет, зависящий от себя, даёт цикл и в обратном обходе."""
        graph = build_graph(repo("A: A B\nB:\n"), "A", 10, reverse=True)
        self.assertEqual(find_cycles(graph), [["A", "A"]])

    def test_reverse_missing_root(self):
        """Отсутствующий пакет вызывает ошибку и в обратном режиме."""
        with self.assertRaises(RepositoryError):
            build_graph(repo(TREE), "Z", 10, reverse=True)

    def test_reverse_long_chain_without_recursion(self):
        """Длинная цепочка обходится в обратную сторону без рекурсии."""
        size = LONG_CHAIN_SIZE
        graph = build_graph(
            chain_repository(size), f"P{size - 1}", size, reverse=True
        )
        self.assertEqual(len(graph.levels), size)


if __name__ == "__main__":
    unittest.main()
