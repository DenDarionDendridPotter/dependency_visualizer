"""Вывод графа зависимостей в виде ASCII-дерева.

Дерево рисуется обходом в глубину с явным стеком (без рекурсии).
Пакет, который встретился повторно, раскрывается только в первом
месте, дальше рядом с ним пометка. Так общая зависимость не
дублируется, а цикл не уводит вывод в бесконечность.
"""

BRANCH = "|-- "
LAST = "`-- "
PIPE = "|   "
SPACE = "    "
SEEN_NOTE = " (см. выше)"
CYCLE_NOTE = " (цикл)"
CUT_NOTE = " ..."


def tree_heading(graph):
    """Собрать заголовок дерева.

    :param graph: построенный граф.
    :returns: первая строка вывода.
    """
    kind = "обратных зависимостей" if graph.reverse else "зависимостей"
    return f"ASCII-дерево {kind} пакета {graph.root}:"


def push_children(stack, graph, node, prefix, depth):
    """Положить на стек потомков пакета так, чтобы первый вышел первым.

    :param stack: стек элементов (имя, отступ, последний ли, глубина).
    :param graph: построенный граф.
    :param node: пакет, потомки которого кладутся на стек.
    :param prefix: отступ для потомков.
    :param depth: глубина потомков в дереве.
    """
    children = graph.links.get(node, [])
    last_index = len(children) - 1
    for index in range(last_index, -1, -1):
        stack.append((children[index], prefix, index == last_index, depth))


def classify(graph, name, path, seen):
    """Решить, как показать пакет: пометка и нужно ли раскрывать его.

    :param graph: построенный граф.
    :param name: имя пакета.
    :param path: пакеты на пути от корня к родителю.
    :param seen: пакеты, уже раскрытые в дереве (изменяется).
    :returns: кортеж (пометка, раскрывать ли потомков).
    """
    cut = CUT_NOTE if name in graph.truncated else ""
    if name in path:
        return CYCLE_NOTE + cut, False
    if name in seen:
        again = SEEN_NOTE if graph.links.get(name) else ""
        return again + cut, False
    seen.add(name)
    return cut, True


def format_tree(graph):
    """Нарисовать граф зависимостей ASCII-деревом.

    :param graph: построенный граф.
    :returns: многострочный текст: заголовок и дерево.
    """
    root_note = CUT_NOTE if graph.root in graph.truncated else ""
    lines = [tree_heading(graph), graph.root + root_note]
    path = [graph.root]
    seen = {graph.root}
    stack = []
    push_children(stack, graph, graph.root, "", 1)
    while stack:
        name, prefix, is_last, depth = stack.pop()
        del path[depth:]
        note, expand = classify(graph, name, path, seen)
        lines.append(prefix + (LAST if is_last else BRANCH) + name + note)
        path.append(name)
        if expand:
            deeper = prefix + (SPACE if is_last else PIPE)
            push_children(stack, graph, name, deeper, depth + 1)
    return "\n".join(lines)
