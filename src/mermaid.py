"""Описание графа зависимостей на языке диаграмм Mermaid.

Результат можно вставить в любой просмотрщик Mermaid (например,
https://mermaid.live) или в блок ```mermaid в файле Markdown, который
GitHub рисует сам. Стрелка A --> B означает "A зависит от B".

Что есть на диаграмме:

- анализируемый пакет закрашен;
- пакеты, у которых связи не раскрыты из-за ограничения глубины,
  нарисованы пунктирной рамкой;
- рёбра циклических зависимостей красные и толстые.

Имена пакетов могут содержать символы, которые Mermaid не любит в
идентификаторах (точку, плюс), поэтому узлы получают служебные имена
n0, n1, ..., а настоящее имя пакета стоит в подписи.
"""

HEADER = "graph TD"
INDENT = "    "
ROOT_CLASS = "root"
CUT_CLASS = "cut"
ROOT_STYLE = "fill:#ffd966,stroke:#333,stroke-width:2px"
CUT_STYLE = "stroke-dasharray: 5 5"
CYCLE_STYLE = "stroke:#d33,stroke-width:3px"
QUOTE = '"'
QUOTE_ESCAPE = "#quot;"
COMMENT = "%% "


def node_label(name):
    """Подготовить подпись узла: в кавычках, с экранированием кавычек.

    :param name: имя пакета.
    :returns: подпись для Mermaid.
    """
    return QUOTE + name.replace(QUOTE, QUOTE_ESCAPE) + QUOTE


def cycle_pairs(cycles):
    """Собрать пары пакетов, лежащие на циклах.

    :param cycles: найденные циклы, в каждом первый и последний пакет
        совпадают.
    :returns: множество пар (пакет, его зависимость).
    """
    return {
        (cycle[position], cycle[position + 1])
        for cycle in cycles
        for position in range(len(cycle) - 1)
    }


def comment_lines(graph, cycles):
    """Собрать строки-комментарии с описанием графа.

    :param graph: построенный граф.
    :param cycles: найденные циклы.
    :returns: список комментариев Mermaid.
    """
    lines = [COMMENT + graph.title()]
    if cycles:
        lines.extend(
            COMMENT + "цикл: " + " -> ".join(cycle) for cycle in cycles
        )
    else:
        lines.append(COMMENT + "циклические зависимости: нет")
    if graph.truncated:
        cut = [name for name in graph.levels if name in graph.truncated]
        lines.append(
            COMMENT + "связи не раскрыты из-за глубины (пунктирная рамка): "
            + ", ".join(cut)
        )
    return lines


def style_lines(graph, ids, edges, cycles):
    """Собрать строки оформления: классы узлов и стили рёбер.

    :param graph: построенный граф.
    :param ids: словарь имя пакета -> служебное имя узла.
    :param edges: рёбра графа в порядке вывода.
    :param cycles: найденные циклы.
    :returns: список строк Mermaid.
    """
    lines = [
        f"{INDENT}classDef {ROOT_CLASS} {ROOT_STYLE}",
        f"{INDENT}classDef {CUT_CLASS} {CUT_STYLE}",
        f"{INDENT}class {ids[graph.root]} {ROOT_CLASS}",
    ]
    cut = [ids[name] for name in graph.levels if name in graph.truncated]
    if cut:
        lines.append(f"{INDENT}class {','.join(cut)} {CUT_CLASS}")
    on_cycle = cycle_pairs(cycles)
    numbers = [str(i) for i, edge in enumerate(edges) if edge in on_cycle]
    if numbers:
        lines.append(f"{INDENT}linkStyle {','.join(numbers)} {CYCLE_STYLE}")
    return lines


def to_mermaid(graph, cycles):
    """Собрать описание графа на языке Mermaid.

    :param graph: построенный граф.
    :param cycles: найденные в нём циклы.
    :returns: многострочный текст диаграммы.
    """
    ids = {name: f"n{number}" for number, name in enumerate(graph.levels)}
    edges = graph.edges()
    lines = [HEADER]
    lines.extend(INDENT + line for line in comment_lines(graph, cycles))
    lines.extend(
        f"{INDENT}{ids[name]}[{node_label(name)}]" for name in graph.levels
    )
    lines.extend(
        f"{INDENT}{ids[source]} --> {ids[target]}" for source, target in edges
    )
    lines.extend(style_lines(graph, ids, edges, cycles))
    return "\n".join(lines)
