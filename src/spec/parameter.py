

import dataclasses
import itertools
from pathlib import Path

from typing import Any, Dict, List, Tuple

from util import _get, _get_or
from errors import FlootSpecSyntaxError
from spec.spec_item import SpecItem

@dataclasses.dataclass
class Parameter(SpecItem):
    values: List[Any]
    min_occurrence: int
    max_occurrence: int

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Parameter':
        values = _get(content, f'{path}.values', T=list)
        min_o = _get_or(content, f'{path}.occurrence', T=dict, default=dict()).get('min', 1)
        max_o = _get_or(content, f'{path}.occurrence', T=dict, default=dict()).get('max', 1)

        if max_o < min_o:
            raise FlootSpecSyntaxError(f'{path}.occurrence.max is smaller than {path}.occurrence.min')

        return Parameter(
            values=values,
            min_occurrence=min_o,
            max_occurrence=max_o,
        )

    def get_combinations(self) -> List[List[Tuple[str, str]]]:
        combinations = itertools.chain.from_iterable(
            itertools.product(map(str, self.values), repeat=i)
            for i in range(self.min_occurrence, self.max_occurrence+1)
        )
        return list(combinations)


class Parameters(dict):
    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Parameters':
        self = Parameters()
        for name in _get(content, path, T=dict):
            self[name] = Parameter.parse(spec_path, content, f'{path}.{name}')
        return self