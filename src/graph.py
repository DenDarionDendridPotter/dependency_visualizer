"""Граф зависимостей: обход в ширину без рекурсии и поиск циклов.

Обход начинается с анализируемого пакета (глубина 0). Его зависимости
получают глубину 1, их зависимости глубину 2 и так далее. Пакет
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


@dataclass
class Graph:
    """Граф зависимостей, построенный обходом.

    :param root: анализируемый пакет.
    :param max_depth: максимальная глубина анализа.
    :param filter_substring: подстрока, исключающая пакеты из анализа.
    :param levels: пакет -> глубина, в порядке обхода.
    :param links: раскрытый пакет -> список его зависимостей.
    :param truncated: пакеты, у которых зависимости не раскрыты из-за
        ограничения глубины.
    """

    root: str
    max_depth: int
    filter_substring: str = ""
    levels: dict = field(default_factory=dict)
    links: dict = field(default_factory=dict)
    truncated: set = field(default_factory=set)

    def edges(self):
        """Перечислить все зависимости графа.

        :returns: список пар (пакет, пакет, от которого он зависит).
        """
        return [
            (source, target)
            for source, targets in self.links.items()
            for target in targets
        ]


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


def build_graph(repository, root, max_depth, filter_substring=""):
    """Построить граф зависимостей обходом в ширину без рекурсии.

    :param repository: репозиторий пакетов.
    :param root: имя анализируемого пакета.
    :param max_depth: максимальная глубина анализа.
    :param filter_substring: пакеты с этой подстрокой не учитываются.
    :returns: построенный граф.
    :raises RepositoryError: если пакета нет или он исключён фильтром.
    """
    check_root(repository, root, filter_substring)
    graph = Graph(root, max_depth, filter_substring)
    graph.levels[root] = 0
    queue = deque([root])
    while queue:
        node = queue.popleft()
        neighbors = [
            name
            for name in repository.dependencies(node)
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
        первый и последний пакет совпадают.
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
            cycles.append(path[path.index(child):] + [child])
    return cycles
