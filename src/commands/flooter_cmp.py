import itertools
import sys
import requests
import difflib


from termcolor import colored
from typing import Dict, Any, Iterable, Iterator, List, Tuple
from errors import FlooterError, FlooterRunError

from util import _get_or, _get, _box, _merge, _exit_on_exception
from commands.command import Command
from loggers import Logger, bold, color
from spec.floot_spec import FlootSpec
from spec.storage import Storage


def _split(a: Dict, b: Dict, path: str) -> Tuple[Dict, Dict, Dict]:
    a_items = _get_or(a, path, T=dict, default=dict())
    b_items = _get_or(b, path, T=dict, default=dict())

    a_exclusive= set(a_items.keys()).difference(b_items.keys())
    b_exclusive= set(b_items.keys()).difference(a_items.keys())

    # shared endpoints
    shared = set(a_items.keys()).intersection(b_items.keys())

    return a_exclusive, b_exclusive, shared

def _get_header_info(r: requests.Response) -> List[str]:
    return [
        f'Status-Code: {r.status_code}',
        f'Reason: {r.reason}',
        f"Content-Type: {r.headers.get('Content-Type', '')}",
        f"Connection: {r.headers.get('Connection', '')}",
    ]

def _contains_one_of(s: str, l: Iterable[str]) -> bool:
    """
    Returns True if any item in l is a substring of s
    """
    for item in l:
        if item in s:
            return True
    return False

TEXT_BASED_CONTENT_TYPES = ['json', 'text']
SIZE_COMPARABLE_CONTENT_TYPES = ['zip']

class FlooterCompare(Command):
    def __init__(self, spec: FlootSpec, logger: Logger, brief: bool) -> None:
        self.spec = spec
        self.logger = logger
        self.brief = brief
        self.exit_code = 0

    def cmp_headers(self,
                    a_name: str,                # this is a modifed a_name
                    a_resp: requests.Response,
                    b_name: str,                # this is a modifed a_name
                    b_resp: requests.Response,
                    ) -> Iterable[str]:

        a_resp_header_fields = _get_header_info(a_resp)
        b_resp_header_fields = _get_header_info(b_resp)

        return difflib.unified_diff(
            a_resp_header_fields,
            b_resp_header_fields,
            fromfile=a_name,
            tofile=b_name,
            n=0                 # no context lines as they are only key value pairs
        )

    def cmp_body_text(self,
                      a_name: str,
                      a_resp: requests.Response,
                      b_name: str,
                      b_resp: requests.Response
                      ) -> Iterable[str]:

        return difflib.unified_diff(
            a_resp.content.decode('utf-8').splitlines(),
            b_resp.content.decode('utf-8').splitlines(),
            fromfile=a_name,
            tofile=b_name,
        )

    def cmp_body_size(self,
                      a_name: str,
                      a_resp: requests.Response,
                      b_name: str,
                      b_resp: requests.Response
                      ) -> Iterable[str]:

        return difflib.unified_diff(
            [len(a_resp.content)],
            [len(b_resp.content)],
            fromfile=a_name,
            tofile=b_name,
        )

    def cmp_body(self,
                 a_name: str,
                 a_response: requests.Response,
                 b_name: str,
                 b_response: requests.Response
                 ) -> Iterable[str]:

        content_types = [a_response.headers.get('Content-Type'), b_response.headers.get('Content-Type')]

        # compare text-based bodies if they are both text based
        if all([_contains_one_of(ct, TEXT_BASED_CONTENT_TYPES) for ct in content_types]):
            return self.cmp_body_text(a_name, a_response, b_name, b_response)

        # they can be compared based on their type
        elif all([_contains_one_of(ct, SIZE_COMPARABLE_CONTENT_TYPES) for ct in content_types]):
            return self.cmp_body_size(a_name, a_response, b_name, b_response)

        # cannot compare them because it is not yet defined
        else:
            self.logger.it(color(bold(f'Cannot compare Content-Types: {content_types}'), 'yellow'))

        return []

    def cmp_exclusive_request(self,
                              name:          str,
                              storage:       Storage,
                              testset_name:  str,
                              endpoint_name: str,
                              req_id:        str,
                              is_new:        bool
                              ) -> None:
        # whenever something is exclusive it is a change!
        self.exit_code = 1

        display_color = 'green' if is_new else 'red'
        self.logger.writeln(colored(name, color=display_color) + f' > {testset_name} > {endpoint_name} > {req_id}')

        resp: requests.Response = storage.load(req_id)
        self.logger.response(resp, _get(storage.meta, f'testsets.{testset_name}.{endpoint_name}.{req_id}.parameters'), self.brief)

    def cmp_shared_request(self,
                           a_name:          str,
                           a_storage:       Storage,
                           b_name:          str,
                           b_storage:       Storage,
                           testset_name:    str,
                           endpoint_name:   str,
                           req_id:          str
                           ) -> None:
        prompt = f"[{colored(a_name, 'red')} | {colored(b_name, 'green')}] > {testset_name} > {endpoint_name} > {req_id}\n"

        a_resp: requests.Response = a_storage.load(req_id)
        b_resp: requests.Response = b_storage.load(req_id)


        # check if a comperator is defined for the endpoint
        comperator_name = _merge(self.spec.endpoints,
                                 self.spec.testsets.get(testset_name, {'endpoints': {}}).endpoints
                                ).get(endpoint_name).comperator

        # use defualt comperator
        if comperator_name is None:
            # compare headers
            header_diff = list(self.cmp_headers(a_name, a_resp, b_name, b_resp))
            body_diff = list(self.cmp_body(a_name, a_resp, b_name, b_resp))

            for line in _box(prompt, itertools.chain(header_diff, body_diff), '\n'+('-'*40)+'\n'):
                self.logger.write(line)

            # if there is anything to print -> then there was a change
            if len(header_diff) + len(body_diff) > 0:
                self.exit_code = 1

        # a specific comperator should be used
        else:
            if comperator_name not in self.spec.comperators:
                raise FlooterRunError(f'The comperator {comperator_name} that according to the '
                                      f'specification be used for testset {testset_name} and '
                                      f'endpoint {endpoint_name} does not exist. Available are '
                                      f'{", ".join(self.spec.comperators.keys())}')

            # could just check if report is not or not empty but this way it is
            # safer
            had_changes, report = self.spec.comperators[comperator_name](testset_name,
                                                                         endpoint_name,
                                                                         req_id,
                                                                         a_name,
                                                                         a_resp,
                                                                         b_name,
                                                                         b_resp
                                                                        )
            for line in _box(prompt, report, '\n'+('-'*40)+'\n'):
                self.logger.writeln(line)

            self.exit_code = 1 if had_changes else self.exit_code


    def cmp_exclusive_endpoint(self,
                               name:            str,    # rid / main
                               storage:         Storage,
                               testset_name:    str,
                               endpoint_name:   str,
                               is_new:          bool
                               ) -> None:
        for req_id in _get(storage.meta, f'testsets.{testset_name}.{endpoint_name}'):
            self.cmp_exclusive_request(name, storage, testset_name, endpoint_name, req_id, is_new)

    def cmp_shared_endpoint(self,
                            a_name:         str,        # rid / main
                            a_storage:      Storage,
                            b_name:         str,        # rid
                            b_storage:      Storage,
                            testset_name:   str,
                            endpoint_name:  str,
                            ) -> None:
        x = _split(a_storage.meta, b_storage.meta, f'testsets.{testset_name}.{endpoint_name}')
        a_exclusive_requests, b_exclusive_requests, shared_requests = x

        for req_id in a_exclusive_requests:
            self.cmp_exclusive_request(a_name, a_storage, testset_name, endpoint_name, req_id, False)

        for req_id in b_exclusive_requests:
            self.cmp_exclusive_request(b_name, b_storage, testset_name, endpoint_name, req_id, True)

        for req_id in shared_requests:
            self.cmp_shared_request(
                a_name,
                a_storage,
                b_name,
                b_storage,
                testset_name,
                endpoint_name,
                req_id
            )

    def cmp_exclusive_testset(self,
                              name:            str,        # rid / main
                              storage:         Storage,
                              testset_name:    str,
                              is_new:          bool        # cmp old new
                              ) -> None:

        for endpoint in _get(storage.meta, f'testsets.{testset_name}'):
            self.cmp_exclusive_endpoint(name, storage, testset_name, endpoint, is_new)

    def cmp_shared_testset(self,
                            a_name:            str,        # rid / main
                            a_storage:         Storage,
                            b_name:            str,        # rid / main
                            b_storage:         Storage,
                            testset_name:     str,
                            ) -> None:

        # for line length
        x = _split(a_storage.meta, b_storage.meta, f'testsets.{testset_name}')
        a_exclusive_endpoints, b_exclusive_endpoints, shared_endpoints = x

        for endpoint in a_exclusive_endpoints:
            self.cmp_exclusive_endpoint(a_name, a_storage, testset_name, endpoint, False)

        for endpoint in b_exclusive_endpoints:
            self.cmp_exclusive_endpoint(b_name, b_storage, testset_name, endpoint, True)

        for endpoint in shared_endpoints:
            self.cmp_shared_endpoint(
                a_name,
                a_storage,
                b_name,
                b_storage,
                testset_name,
                endpoint
            )


    def cmp(self,
            a_name:     str,        # a is old
            a_storage:  Storage,
            b_name:     str,        # b is new
            b_storage:  Storage
            ) -> None:

        # for line length
        x = _split(a_storage.meta, b_storage.meta, 'testsets')
        a_exclusive_testsets, b_exclusive_testsets, shared_testsets = x

        for testset in a_exclusive_testsets:
            self.cmp_exclusive_testset(a_name, a_storage, testset, False)

        for testset in b_exclusive_testsets:
            self.cmp_exclusive_testset(b_name, b_storage, testset, True)

        for testset in shared_testsets:
            self.cmp_shared_testset(
                a_name,
                a_storage,
                b_name,
                b_storage,
                testset
            )

    @_exit_on_exception(FlooterError)
    def run(self, a: str, b: str, *args, **kwargs):
        self.logger.begin()

        if b is None:
            self.cmp(
                'main',
                self.spec.storages.main,
                a,
                self.spec.storages.get_run_storage(a)
            )
        else:
            self.cmp(
                a,
                self.spec.storages.get_run_storage(a),
                b,
                self.spec.storages.get_run_storage(b)
            )

        # exit 0 if no difference, exit 1 otherwise
        sys.exit(self.exit_code)
