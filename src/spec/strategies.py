import abc
import itertools
import operator
import dataclasses

from functools import reduce
from pathlib import Path
from typing import Any, Tuple, Iterable, Dict, List, Union

from util import _get, _get_or
from spec.parameter import Parameters
from spec.spec_item import SpecItem

YAML_TYPES = Union[str, int, float, dict, list]

@dataclasses.dataclass(init=False)
class Strategy(SpecItem):
    name: str
    args: Dict[str, YAML_TYPES]

    def __init__(self, name: str = 'permutations', args: Dict = {}) -> None:
        self.name = name
        self.args = args

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Strategy':
        return Strategy(
            name = _get(content, f'{path}.name', T=str),
            args = _get_or(content, f'{path}.args', T=dict, default=dict()),
        )

def to_powerset(*l: List[Any])  -> Iterable:
    return itertools.chain.from_iterable(
        itertools.combinations(l, r) for r in range(len(l)+1)
    )

def permutations_strategy(testset_name: str,
                          endpoint_name: str,
                          vars: Dict[str, str],
                          args: Dict[str, YAML_TYPES],
                          parameters: Parameters
                          ) -> List[List[Tuple[str, str]]]:
    # 'application': [[], [('application', 1)], [('application', 2)], [('application', 1), ('application', 1)].....
    # 'limit': [[('limit', 1000)], [('limit', 0)], [('limit', 'None')]]}
    names_with_values = [
            list(list(zip(itertools.repeat(name), comb)) for comb in parameter.get_combinations())
            for name, parameter in parameters.items()
    ]

    return list(map(lambda comb: reduce(operator.add, comb, list()), itertools.product(*names_with_values)))

STRATEGY_MAPPING = {
    'permutations': permutations_strategy
}
