

import dataclasses
from pathlib import Path

from typing import Dict, Optional


from util import _call_if, _get
from spec.hooks import Hooks
from spec.parameter import Parameters
from spec.endpoint import Endpoints
from spec.spec_item import SpecItem

@dataclasses.dataclass
class TestSet:
    hooks:      Optional[Hooks]
    parameters: Optional[Parameters]
    endpoints:  Optional[Endpoints]

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'TestSet':
        return TestSet(
            hooks       =_call_if(content, f'{path}.hooks',     lambda: Hooks.parse(spec_path, content, f'{path}.hooks')),
            parameters  =_call_if(content, f'{path}.parameters',lambda: Parameters.parse(spec_path, content, f'{path}.parameters')),
            endpoints   =_call_if(content, f'{path}.endpoints', lambda: Endpoints.parse(spec_path, content, f'{path}.endpoints')),
        )

class TestSets(dict, SpecItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'TestSets':
        return TestSets({name: TestSet.parse(spec_path, content, f'{path}.{name}') for name in _get(content, path, T=dict)})
