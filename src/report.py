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


def format_graph(graph, cycles):
    """Собрать отчёт: уровни, зависимости, ограничения и циклы.

    :param graph: построенный граф.
    :param cycles: найденные в нём циклы.
    :returns: многострочный текст.
    """
    substring = graph.filter_substring or NO_FILTER_TEXT
    lines = [
        f"граф зависимостей пакета {graph.root} "
        f"(глубина анализа: {graph.max_depth}, фильтр: {substring})"
    ]
    for level, names in group_levels(graph).items():
        lines.append(f"уровень {level}: {', '.join(names)}")
    edges = graph.edges()
    lines.append("зависимости:")
    lines.extend(f"  {source} -> {target}" for source, target in edges)
    if not edges:
        lines.append("  нет")
    lines.append(f"пакетов: {len(graph.levels)}, зависимостей: {len(edges)}")
    if graph.truncated:
        cut = [name for name in graph.levels if name in graph.truncated]
        lines.append(
            "зависимости не раскрыты из-за ограничения глубины у: "
            + ", ".join(cut)
        )
    lines.extend(format_cycles(cycles))
    return "\n".join(lines)
