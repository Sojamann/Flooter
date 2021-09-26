from pathlib import Path
from typing import Dict

from util import _get, _to_absolute_path, _error_if_ukn, _load_mod
from errors import FlootSpecSyntaxError
from spec.spec_item import SpecItem

class FunctionMapper(dict, SpecItem):
    """ Used for transformers and comperators
    transformers:
        source: run/transformers.py
        names:
            tabletransformer: tabletransformer"""

    ITEMS = ['source', 'names']

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'FunctionMapper':
        _error_if_ukn(content, path, FunctionMapper.ITEMS)

        source_path = _to_absolute_path(spec_path, Path(_get(content, f'{path}.source', T=str)))
        if not source_path.is_file():
            raise FlootSpecSyntaxError(f'expected {path}.source to contain a existing file path. Found {source_path}')

        self = FunctionMapper()

        mod = _load_mod(source_path)
        for name, method_name in _get(content, f'{path}.names', T=dict).items():
            if not hasattr(mod, method_name):
                raise FlootSpecSyntaxError(f'The method {method_name} specified {path}.{name} does not exist in source definition of {path}')

            self[name] = getattr(mod, method_name)
        return self
