"""Граф зависимостей: обход в ширину без рекурсии и поиск циклов.

Обход начинается с анализируемого пакета (глубина 0). Его зависимости
получают глубину 1, их зависимости глубину 2 и так далее. Для
обратных зависимостей (кто зависит от пакета) обход тот же, но
"соседями" пакета считаются пакеты, которые зависят от него. Пакет
попадает в граф один раз, на самой маленькой глубине, на которой он
встретился. Это же гарантирует конец обхода при циклических
зависимостях: уже встреченный пакет повторно в очередь не ставится.
Пакеты на предельной глубине в очередь попадают, но их зависимости не
раскрываются.
"""

from collections import deque
from dataclasses import dataclass, field

from .errors import RepositoryError

ACTIVE = "active"
DONE = "done"
NO_FILTER_TEXT = "нет"


@dataclass
class Graph:
    """Граф зависимостей, построенный обходом.

    :param root: анализируемый пакет.
    :param max_depth: максимальная глубина анализа.
    :param filter_substring: подстрока, исключающая пакеты из анализа.
    :param levels: пакет -> глубина, в порядке обхода.
    :param links: раскрытый пакет -> список его зависимостей.
    :param truncated: пакеты, у которых связи не раскрыты из-за
        ограничения глубины.
    :param reverse: True для обратных зависимостей: тогда связи
        пакета это пакеты, которые зависят от него.
    """

    root: str
    max_depth: int
    filter_substring: str = ""
    levels: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)
    truncated: set = field(default_factory=set)
    reverse: bool = False

    def edges(self):
        """Перечислить все зависимости графа.

        Каждая зависимость это пара (пакет, пакет, от которого он
        зависит), независимо от направления обхода.

        :returns: список пар.
        """
        pairs = [
            (source, target)
            for source, targets in self.links.items()
            for target in targets
        ]
        if self.reverse:
            return [(target, source) for source, target in pairs]
        return pairs

    def title(self):
        """Описать граф одной строкой для подписи к выводу.

        :returns: строка с видом графа, пакетом, глубиной и фильтром.
        """
        kind = "обратные зависимости" if self.reverse else "зависимости"
        substring = self.filter_substring or NO_FILTER_TEXT
        return (
            f"{kind} пакета {self.root} "
            f"(глубина анализа: {self.max_depth}, фильтр: {substring})"
        )


def is_excluded(name, substring):
    """Проверить, исключён ли пакет фильтром.

    :param name: имя пакета.
    :param substring: подстрока фильтра, пустая означает "без фильтра".
    :returns: True, если имя содержит подстроку.
    """
    return bool(substring) and substring in name


def check_root(repository, root, substring):
    """Проверить, что анализируемый пакет можно анализировать.

    :param repository: репозиторий пакетов.
    :param root: имя анализируемого пакета.
    :param substring: подстрока фильтра.
    :raises RepositoryError: если пакета нет или он исключён фильтром.
    """
    if not repository.has(root):
        raise RepositoryError(f"пакет {root} не найден в репозитории")
    if is_excluded(root, substring):
        raise RepositoryError(
            f"пакет {root} исключён фильтром {substring!r}: "
            "его имя содержит подстроку фильтра"
        )


def build_graph(
    repository, root, max_depth, filter_substring="", reverse=False
):
    """Построить граф зависимостей обходом в ширину без рекурсии.

    Один и тот же обход строит и прямые зависимости (от чего зависит
    пакет), и обратные (кто зависит от пакета): меняется только
    способ получить соседей пакета.

    :param repository: репозиторий пакетов.
    :param root: имя анализируемого пакета.
    :param max_depth: максимальная глубина анализа.
    :param filter_substring: пакеты с этой подстрокой не учитываются.
    :param reverse: True для обратных зависимостей.
    :returns: построенный граф.
    :raises RepositoryError: если пакета нет или он исключён фильтром.
    """
    check_root(repository, root, filter_substring)
    graph = Graph(root, max_depth, filter_substring, reverse=reverse)
    lookup = repository.dependents if reverse else repository.dependencies
    graph.levels[root] = 0
    queue = deque([root])
    while queue:
        node = queue.popleft()
        neighbors = [
            name
            for name in lookup(node)
            if not is_excluded(name, filter_substring)
        ]
        if graph.levels[node] >= max_depth:
            if neighbors:
                graph.truncated.add(node)
            continue
        graph.links[node] = neighbors
        for name in neighbors:
            if name not in graph.levels:
                graph.levels[name] = graph.levels[node] + 1
                queue.append(name)
    return graph


def find_cycles(graph):
    """Найти циклические зависимости в построенном графе.

    Используется обход в глубину с явным стеком (без рекурсии): если
    зависимость ведёт в пакет, который сейчас находится на пути обхода,
    найден цикл.

    :param graph: построенный граф.
    :returns: список циклов, каждый цикл это список имён, в котором
        первый и последний пакет совпадают, а каждый следующий пакет
        это зависимость предыдущего.
    """
    cycles = []
    state = {graph.root: ACTIVE}
    path = [graph.root]
    stack = [iter(graph.links.get(graph.root, ()))]
    while stack:
        child = next(stack[-1], None)
        if child is None:
            state[path.pop()] = DONE
            stack.pop()
        elif child not in state:
            state[child] = ACTIVE
            path.append(child)
            stack.append(iter(graph.links.get(child, ())))
        elif state[child] == ACTIVE:
            cycle = path[path.index(child):] + [child]
            cycles.append(cycle[::-1] if graph.reverse else cycle)
    return cycles
