from pathlib import Path
import yaml
import dataclasses

from typing import Optional

from util import _get, _call_if, _call_if_exists_or
from spec.request import Request
from spec.testset import TestSets
from spec.hooks import Hooks
from spec.function_mapper import FunctionMapper
from spec.endpoint import Endpoints
from spec.parameter import Parameters
from spec.storage import Storages

@dataclasses.dataclass
class FlootSpec:
    spec_path:      Path
    host:         str
    testsets:       TestSets
    storages:       Storages
    request:        Request
    hooks:          Optional[Hooks]
    strategies:     Optional[FunctionMapper]
    transformers:   Optional[FunctionMapper]
    comperators:    Optional[FunctionMapper]
    endpoints:      Optional[Endpoints]
    parameters:     Optional[Parameters]

    @classmethod
    def load_from_file(cls, spec_path: Path) -> 'FlootSpec':
        with open(spec_path, 'r', encoding='utf-8') as spec_steam:
            content = yaml.load(spec_steam, Loader=yaml.FullLoader)

            # TODO there has to be some default
            return FlootSpec(
                spec_path   =spec_path,
                host      =_get(content, 'host'),
                storages    =Storages.parse(spec_path, content, 'storage'),
                testsets    =TestSets.parse(spec_path, content, 'testsets'),
                request     =_call_if_exists_or(content,
                                                'request',
                                                lambda: Request.parse(spec_path, content, 'request'),
                                                lambda: Request()
                                                ),
                hooks       =_call_if_exists_or(content,
                                                'hooks',
                                                lambda: Hooks.parse(spec_path, content, 'hooks'),
                                                lambda: Hooks()
                                                ),
                strategies  =_call_if_exists_or(content,
                                                'strategies',
                                                lambda: FunctionMapper.parse(spec_path, content, 'strategies'),
                                                lambda: FunctionMapper()
                                                ),
                transformers=_call_if_exists_or(content,
                                                'transformers',
                                                lambda: FunctionMapper.parse(spec_path, content, 'transformers'),
                                                lambda: FunctionMapper()
                                                ),
                comperators =_call_if_exists_or(content,
                                                'comperators',
                                                lambda: FunctionMapper.parse(spec_path, content, 'comperators'),
                                                lambda: FunctionMapper()
                                                ),
                endpoints   =_call_if_exists_or(content,
                                                'endpoints',
                                                lambda: Endpoints.parse(spec_path, content, 'endpoints'),
                                                lambda: Endpoints()
                                                ),
                parameters  =_call_if_exists_or(content,
                                                'parameters',
                                                lambda: Parameters.parse(spec_path, content, 'parameters'),
                                                lambda: Parameters()
                                                ),
            )

