"""Тесты описания графа на языке Mermaid."""

import unittest

from src.graph import build_graph, find_cycles
from src.mermaid import cycle_pairs, node_label, to_mermaid
from tests.test_graph import CYCLE, DIAMOND, TREE, repo


def diagram(text, root="A", depth=10, substring="", reverse=False):
    """Построить граф и получить строки его диаграммы.

    :param text: содержимое тестового репозитория.
    :param root: анализируемый пакет.
    :param depth: максимальная глубина.
    :param substring: подстрока фильтра.
    :param reverse: True для обратных зависимостей.
    :returns: список строк диаграммы.
    """
    graph = build_graph(repo(text), root, depth, substring, reverse)
    return to_mermaid(graph, find_cycles(graph)).splitlines()


class LabelTest(unittest.TestCase):
    """Проверки подписей узлов."""

    def test_label_is_quoted(self):
        """Подпись стоит в кавычках."""
        self.assertEqual(node_label("curl"), '"curl"')

    def test_special_characters_stay_in_label(self):
        """Точки, плюсы и дефисы допустимы внутри подписи."""
        self.assertEqual(node_label("libstdc++"), '"libstdc++"')
        self.assertEqual(node_label("lua5.4-curl"), '"lua5.4-curl"')

    def test_quote_is_escaped(self):
        """Кавычка внутри имени заменяется кодом Mermaid."""
        self.assertEqual(node_label('a"b'), '"a#quot;b"')

    def test_cycle_pairs(self):
        """Пары пакетов на цикле берутся из соседних элементов."""
        self.assertEqual(
            cycle_pairs([["A", "B", "C", "A"]]),
            {("A", "B"), ("B", "C"), ("C", "A")},
        )
        self.assertEqual(cycle_pairs([]), set())


class DiagramTest(unittest.TestCase):
    """Проверки текста диаграммы."""

    def test_header_is_first_line(self):
        """Диаграмма начинается с объявления направления."""
        self.assertEqual(diagram(TREE)[0], "graph TD")

    def test_nodes_and_edges(self):
        """Узлы идут в порядке обхода, рёбра повторяют зависимости."""
        lines = diagram("A: B C\nB:\nC:\n")
        self.assertIn('    n0["A"]', lines)
        self.assertIn('    n1["B"]', lines)
        self.assertIn('    n2["C"]', lines)
        self.assertIn("    n0 --> n1", lines)
        self.assertIn("    n0 --> n2", lines)

    def test_shared_node_has_two_incoming_edges(self):
        """Общая зависимость получает ребро от каждого пакета."""
        lines = diagram(DIAMOND)
        self.assertIn("    n1 --> n3", lines)
        self.assertIn("    n2 --> n3", lines)

    def test_root_is_highlighted(self):
        """Корень закрашен."""
        self.assertIn("    class n0 root", diagram(TREE))

    def test_no_cut_class_without_truncation(self):
        """Если всё раскрыто, пунктирный класс не назначается."""
        self.assertFalse(
            any(line.startswith("    class n") and "cut" in line
                for line in diagram(TREE))
        )

    def test_truncated_nodes_are_dashed(self):
        """Пакеты с нераскрытыми связями получают пунктирную рамку."""
        lines = diagram(TREE, depth=1)
        self.assertIn("    class n1,n2 cut", lines)

    def test_no_cycle_style_without_cycles(self):
        """Без циклов рёбра не перекрашиваются."""
        self.assertFalse(any("linkStyle" in line for line in diagram(TREE)))

    def test_cycle_edges_are_styled(self):
        """Рёбра цикла A -> B -> C -> A выделены, ребро C -> D нет."""
        lines = diagram(CYCLE)
        self.assertIn("    n2 --> n0", lines)
        styled = [line for line in lines if "linkStyle" in line]
        self.assertEqual(len(styled), 1)
        self.assertIn("linkStyle 0,1,2 ", styled[0])

    def test_self_loop(self):
        """Зависимость пакета от себя рисуется петлёй и выделяется."""
        lines = diagram("A: A\n")
        self.assertIn("    n0 --> n0", lines)
        self.assertTrue(any("linkStyle 0 " in line for line in lines))

    def test_reverse_arrows_point_to_dependency(self):
        """В обратном графе стрелки идут от зависящего к зависимости."""
        lines = diagram(TREE, root="D", reverse=True)
        self.assertIn('    n0["D"]', lines)
        self.assertIn("    n1 --> n0", lines)
        self.assertIn("    n2 --> n1", lines)

    def test_comments_describe_graph(self):
        """Комментарии содержат описание графа и сведения о циклах."""
        lines = diagram(CYCLE, depth=10, substring="Z")
        comments = [line.strip() for line in lines if "%%" in line]
        self.assertIn("%% зависимости пакета A (глубина анализа: 10, "
                      "фильтр: Z)", comments)
        self.assertIn("%% цикл: A -> B -> C -> A", comments)

    def test_comment_without_cycles(self):
        """Если циклов нет, об этом сказано в комментарии."""
        self.assertIn("    %% циклические зависимости: нет", diagram(TREE))

    def test_comment_lists_truncated(self):
        """Нераскрытые из-за глубины пакеты перечислены в комментарии."""
        text = "\n".join(diagram(TREE, depth=1))
        self.assertIn("(пунктирная рамка): B, C", text)

    def test_every_edge_endpoint_is_declared(self):
        """Каждый конец ребра объявлен как узел."""
        lines = diagram("A: B C\nB: D\nC: D\nD: E\nE: A\n")
        declared = {line.split("[")[0].strip()
                    for line in lines if '["' in line}
        used = {part for line in lines if " --> " in line
                for part in line.split(" --> ")}
        self.assertTrue({part.strip() for part in used} <= declared)


if __name__ == "__main__":
    unittest.main()
