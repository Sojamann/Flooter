import dataclasses

from typing import Dict
from pathlib import Path

from util import _get_or
from spec.spec_item import SpecItem

@dataclasses.dataclass(init=False)
class Request(SpecItem):

    header: Dict[str, str]

    def __init__(self, **kwargs) -> None:
        self.header = kwargs.get('header', dict())

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Request':
        return Request(header = _get_or(content, f'{path}.header', T=dict, default=dict()))