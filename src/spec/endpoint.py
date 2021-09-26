

import dataclasses
from pathlib import Path
from typing import Dict, List, Optional

from util import _get, _get_or, _call_if_exists_or, _call_if
from errors import FlootSpecSyntaxError
from spec.strategies import Strategy
from spec.parameter import Parameters
from spec.spec_item import SpecItem


@dataclasses.dataclass
class Endpoint(SpecItem):
    ITEM_NAMES = ['transformer', 'comperator', 'uses', 'strategy', 'parameters']

    strategy:       Strategy
    transformer:    Optional[str]
    type:           Optional[str]
    comperator:     Optional[str]
    uses:           Optional[List[str]]
    parameters:     Optional[Parameters]

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Endpoint':
        # error on unkown
        ukn = set(_get(content, path).keys()).difference(Endpoint.ITEM_NAMES)
        if len(ukn) != 0:
            raise FlootSpecSyntaxError(f'Found {ukn} in path. Only {Endpoint.ITEM_NAMES} are allowed')

        return Endpoint(transformer =_get_or(content,
                                             f'{path}.transformer',
                                             T=str),
                        comperator  =_get_or(content,
                                             f'{path}.comperator',
                                             T=str),
                        type = _get_or(content,
                                       f'{path}.type',
                                       T=str,
                                       default='get',
                                       choices=['get', 'post', 'delete', 'put']),
                        uses        =_get_or(content,
                                             f'{path}.uses',
                                             T=list),
                        strategy    =_call_if_exists_or(content,
                                                        f'{path}.strategy',
                                                        lambda: Strategy.parse(spec_path, content, f'{path}.strategy'),
                                                        lambda: Strategy()
                                                        ),
                        parameters  =_call_if(content,
                                              f'{path}.parameters',
                                              lambda: Parameters.parse(spec_path, content, f'{path}.parameters')))

class Endpoints(dict):
    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Endpoints':
        return Endpoints({name: Endpoint.parse(spec_path, content, f'{path}.{name}') for name in _get(content, path, T=dict)})
