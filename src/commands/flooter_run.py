import sys
import re
import urllib.parse
import uuid
import hashlib
import inspect

from typing import Any, Callable, List, Tuple

import requests

from commands.command import Command
from loggers import Logger
from spec.strategies import STRATEGY_MAPPING
from util import _coalesce_fns, _set, _merge, _exit_on_exception
from spec.floot_spec import FlootSpec
from spec.endpoint import Endpoint
from spec.testset import TestSet
from errors import FlooterError, FlooterRunError

def enrich_err(func: Callable) -> Callable:
    """
    This decorator enriches a FlooterError with the content of parameters

    @enrich_err
    def x(a_name, a_content, b_name, b_content):
        raise FlooterError('.... details')

    try:
        x('A', None, 'b', None)
    except FlooterError as err:
        err.message() == 'A > b: .... details
    """
    sig = inspect.signature(func)
    idxs = [idx for idx, name in enumerate(sig.parameters) if name.endswith('_name')]

    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FlooterError as err:
            # only enrich if not enriched already
            if not err.is_enriched:
                # print what the named params are
                raise err.enrich(' > '.join([a for idx, a in enumerate(args) if idx in idxs]) + ':')
            else:
                raise err

    return _inner

class FlooterRun(Command):
    TEMPLATE_RE: re.Pattern = re.compile(r'^\{\{(\w+)\}\}$')

    def __init__(self, spec: FlootSpec, logger: Logger) -> None:
        self.spec = spec
        self.logger = logger
        self.run_id = self._generate_run_id()
        self.run_storage = spec.storages.make_run_storage(self.run_id)

        _set(self.run_storage.meta, 'rid', self.run_id)

        self.vars = dict()

    def _generate_run_id(self) -> str:
        return str(uuid.uuid4())

    def _generate_request_id(self,
                             testset_name: str,
                             endpoint_name: str,
                             param_combination: List[Tuple[str, Any]]) -> str:
        hasher = hashlib.sha256()
        hasher.update(endpoint_name.encode())
        hasher.update(testset_name.encode())
        for name, value in param_combination:
            hasher.update(name.encode())
            hasher.update(str(value).encode()) # Any to str -> must always be the same
        return hasher.hexdigest()

    def _encode_param(self, param: Tuple[str, Any]) -> Tuple[str, Any]:
        return (param[0], urllib.parse.quote_plus(str(param[1])))

    def _enrich(self, name: str) -> str:
        template_match = FlooterRun.TEMPLATE_RE.match(name)

        if template_match is not None:
            var_name = template_match.group(1)

            if var_name not in self.vars:
                self.logger.warn(f'{var_name} is not a known variable!!')
            return self.vars.get(var_name, '')

        return name

    def _enrich_param(self, param: Tuple[str, str]) -> Tuple[str, str]:
        return (param[0], self._enrich(param[1]))

    @enrich_err
    def _run_request(self,
                     testset_name: str,
                     testset: TestSet,
                     endpoint_name: str,
                     endpoint: Endpoint,
                     param_combination: List[Tuple[str, str]]):

        before_req_hook = _coalesce_fns(testset.hooks.before_request, self.spec.hooks.before_request)
        before_req_hook(testset_name, endpoint_name, param_combination, self.vars)

        req_id = self._generate_request_id(testset_name, endpoint_name, param_combination)

        # if a transformer is specified, it must exist!
        if endpoint.transformer is not None and endpoint.transformer not in self.spec.transformers:
            raise FlooterRunError(f'uses the {endpoint.transformer} transformer but it was never defiend!')
        transformer = self.spec.transformers.get(endpoint.transformer, lambda tn, en, resp: resp)

        # do string interpolation
        param_combination = [self._enrich_param(param) for param in param_combination]
        interpolated_endpoint_name = '/'.join(map(self._enrich, endpoint_name.split('/')))

        if endpoint.type.lower() == 'get':
            # make the request
            resp = requests.get(f'{self.spec.host}/{interpolated_endpoint_name}',
                                map(self._encode_param, param_combination),
                                headers={k: self._enrich(v) for k, v in self.spec.request.header.items()}
                                )
            # let a defined transformer make changes, defaults to identity function
            resp = transformer(resp)
            # safe some meta information
            _set(self.run_storage.meta, f'testsets.{testset_name}.{endpoint_name}.{req_id}.parameters', param_combination)
            # save the actual response under the req_id name
            self.run_storage.save(req_id, resp)

        after_req_hook = _coalesce_fns(testset.hooks.after_request, self.spec.hooks.after_request)
        after_req_hook(testset_name, endpoint_name, param_combination, self.vars)
        return (req_id, param_combination)

    @enrich_err
    def _run_endpoint(self,
                      testset_name:     str,
                      testset:          TestSet,
                      endpoint_name:    str,
                      endpoint:         Endpoint
                      ) -> None:
        self.logger.writeln(f'{testset_name} > {endpoint_name}', ['bold', 'underline'])
        _coalesce_fns(self.spec.hooks.before_endpoint, testset.hooks.before_endpoint)(testset_name, endpoint_name, self.vars)

        avail_params = _merge(self.spec.parameters, testset.parameters, endpoint.parameters)

        # error if a param is used that is not defined
        ukn_params = [p for p in endpoint.uses if p not in avail_params]
        if len(ukn_params):
            raise FlooterRunError(f'Endpoint uses undefined parameters '
                                  f'{ukn_params} available are {list(avail_params.keys())}')

        # get used params
        params = {k: v for k, v in avail_params.items() if k in endpoint.uses}

        # generate requests based on strategy
        strategy = _merge(STRATEGY_MAPPING, self.spec.strategies).get(endpoint.strategy.name)
        if strategy is None:
            raise FlooterRunError(f'Strategy {endpoint.strategy} is not known')
        runs = strategy(testset_name, endpoint_name, self.vars, endpoint.strategy.args, params)
        requests = [self._run_request(testset_name, testset, endpoint_name, endpoint, combination)
                    for combination in runs]

        if len(requests) > 0:
            # generate data for table
            columns = ['request id'] + endpoint.uses
            rows = []
            for rid, params in requests:
                entry = dict({k: list([]) for k in columns})
                entry['request id'] = [rid]
                for name, value in params:
                    entry[name].append(value)
                rows.append(entry)
            self.logger.table(columns, rows)

        _coalesce_fns(self.spec.hooks.after_endpoint, testset.hooks.after_endpoint)(testset_name, endpoint_name, self.vars)

    @enrich_err
    def _run_testset(self, testset_name: str, testset: TestSet):
        _coalesce_fns(testset.hooks.before_testset, self.spec.hooks.before_testset)(testset_name, self.vars)

        # set and/or override endpoints
        endpoints = _merge(self.spec.endpoints, testset.endpoints)

        for endpoint_name, endpoint in endpoints.items():
            self._run_endpoint(testset_name, testset, endpoint_name, endpoint)

        _coalesce_fns(testset.hooks.after_testset, self.spec.hooks.after_testset)(testset_name, self.vars)

    @_exit_on_exception(FlooterError)
    def run(self):
        # write out run_id which is entirely independent from any logging logic
        sys.stdout.write(str(self.run_id))
        sys.stdout.write('\n')

        self.logger.begin()

        _coalesce_fns(self.spec.hooks.before_all)(self.vars)

        for name, testset in self.spec.testsets.items():
            self._run_testset(name, testset)

        _coalesce_fns(self.spec.hooks.after_all)(self.vars)

        sys.exit(0)

