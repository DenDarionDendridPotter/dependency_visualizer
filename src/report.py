"""Текстовый отчёт о построенном графе зависимостей."""

NO_FILTER_TEXT = "нет"
CYCLE_ARROW = " -> "


def group_levels(graph):
    """Сгруппировать пакеты графа по глубине.

    :param graph: построенный граф.
    :returns: словарь глубина -> список пакетов в порядке обхода.
    """
    groups = {}
    for name, level in graph.levels.items():
        groups.setdefault(level, []).append(name)
    return groups


def format_cycles(cycles):
    """Собрать строки о циклических зависимостях.

    :param cycles: найденные циклы.
    :returns: список строк отчёта.
    """
    if not cycles:
        return ["циклические зависимости: нет"]
    lines = [f"циклические зависимости ({len(cycles)}):"]
    lines.extend("  " + CYCLE_ARROW.join(cycle) for cycle in cycles)
    return lines


def format_title(graph):
    """Собрать заголовок отчёта.

    :param graph: построенный граф.
    :returns: первая строка отчёта.
    """
    substring = graph.filter_substring or NO_FILTER_TEXT
    options = f"(глубина анализа: {graph.max_depth}, фильтр: {substring})"
    if graph.reverse:
        return (
            f"обратные зависимости пакета {graph.root}: пакеты, которые "
            f"зависят от него {options}"
        )
    return f"граф зависимостей пакета {graph.root} {options}"


def format_edges(graph):
    """Собрать список зависимостей графа.

    :param graph: построенный граф.
    :returns: строки отчёта, начиная с заголовка списка.
    """
    edges = graph.edges()
    title = "зависимости:"
    if graph.reverse:
        title = "зависимости (A -> B означает: A зависит от B):"
    lines = [title]
    lines.extend(f"  {source} -> {target}" for source, target in edges)
    if not edges:
        lines.append("  нет")
    return lines


def format_totals(graph):
    """Собрать итоговые строки отчёта.

    :param graph: построенный граф.
    :returns: список строк с числом пакетов и нераскрытыми пакетами.
    """
    lines = [
        f"пакетов: {len(graph.levels)}, зависимостей: {len(graph.edges())}"
    ]
    if graph.reverse:
        lines.append(
            f"пакетов, зависящих от {graph.root} прямо или через другие "
            f"пакеты: {len(graph.levels) - 1}"
        )
    if graph.truncated:
        cut = [name for name in graph.levels if name in graph.truncated]
        what = "обратные зависимости" if graph.reverse else "зависимости"
        lines.append(
            f"{what} не раскрыты из-за ограничения глубины у: "
            + ", ".join(cut)
        )
    return lines


def format_graph(graph, cycles):
    """Собрать отчёт: уровни, зависимости, ограничения и циклы.

    :param graph: построенный граф.
    :param cycles: найденные в нём циклы.
    :returns: многострочный текст.
    """
    lines = [format_title(graph)]
    for level, names in group_levels(graph).items():
        lines.append(f"уровень {level}: {', '.join(names)}")
    lines.extend(format_edges(graph))
    lines.extend(format_totals(graph))
    lines.extend(format_cycles(cycles))
    return "\n".join(lines)
