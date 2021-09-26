import dataclasses

from typing import Optional, Callable, Dict, List
from types import ModuleType
from pathlib import Path

from util import _get, _get_or, _error_if_ukn, _to_absolute_path, _load_mod
from errors import FlootSpecSyntaxError
from spec.spec_item import SpecItem

@dataclasses.dataclass(init=False)
class Hooks(SpecItem):
    ITEMS = ['before_all', 'before_testset', 'before_each', 'after_each', 'after_testset', 'after_all', 'source']
    before_all:         Optional[Callable]
    before_testset:     Optional[Callable]
    before_endpoint:    Optional[Callable]
    before_request:     Optional[Callable]
    after_request:      Optional[Callable]
    after_endpoint:     Optional[Callable]
    after_testset:      Optional[Callable]
    after_all:          Optional[Callable]

    def __init__(self, **kwargs) -> None:
        self.before_all         = kwargs.get('before_all',      None)
        self.before_testset     = kwargs.get('before_testset',  None)
        self.before_endpoint    = kwargs.get('before_endpoint', None)
        self.before_request     = kwargs.get('before_request',  None)
        self.after_request      = kwargs.get('after_request',   None)
        self.after_endpoint     = kwargs.get('after_endpoint',  None)
        self.after_testset      = kwargs.get('after_testset',   None)
        self.after_all          = kwargs.get('after_all',       None)

    @classmethod
    def _parse_hook(cls, mod: ModuleType, content: Dict, path: str) -> Callable:
        hook_def = _get_or(content, path, T=dict)
        if hook_def is None:
            return None

        method_name = _get(content, f'{path}.use', T=str)

        if not hasattr(mod, method_name):
            raise FlootSpecSyntaxError(f'The method {method_name} does not exist in the specified source file specified at {path}')

        args = _get_or(content, f'{path}.args', T=dict, default=dict())
        hook_instance = getattr(mod, method_name)(**args)
        return hook_instance

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Hooks':
        _error_if_ukn(content, path, Hooks.ITEMS)

        source_path = _to_absolute_path(spec_path, Path(_get(content, f'{path}.source', T=str)))
        if not source_path.is_file():
            raise FlootSpecSyntaxError(f'expected {path}.source to contain a existing file path. Found {source_path}')

        mod = _load_mod(source_path)

        return Hooks(
            before_all      = Hooks._parse_hook(mod, content, f'{path}.before_all'),
            before_testset  = Hooks._parse_hook(mod, content, f'{path}.before_testset'),
            before_endpoint = Hooks._parse_hook(mod, content, f'{path}.before_endpoint'),
            before_request  = Hooks._parse_hook(mod, content, f'{path}.before_request'),
            after_request   = Hooks._parse_hook(mod, content, f'{path}.after_request'),
            after_endpoint  = Hooks._parse_hook(mod, content, f'{path}.after_endpoint'),
            after_testset   = Hooks._parse_hook(mod, content, f'{path}.after_testset'),
            after_all       = Hooks._parse_hook(mod, content, f'{path}.after_all'),
        )