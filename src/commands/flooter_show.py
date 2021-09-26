import sys
import enum

from commands.command import Command
from errors import FlooterError
from loggers import Logger, bold
from spec.floot_spec import FlootSpec
from spec.storage import Storage
from util import _exit_on_exception

class FlooterShowVerbosity(enum.IntEnum):
    NAME    = enum.auto()
    HEADER  = enum.auto()
    BODY    = enum.auto()

    # for argparse
    def __str__(self) -> str:
        return self.name
    def __repr__(self) -> str:
        return self.__str__()

    # for argparse
    @classmethod
    def from_arg_str(cls, name: str) -> 'FlooterShowVerbosity':
        try:
            return FlooterShowVerbosity[name]
        except KeyError:
            return name


class FlooterShow(Command):
    def __init__(self, spec: FlootSpec, logger: Logger) -> None:
        self.spec = spec
        self.logger = logger


    def show(self,
             name: str,
             storage: Storage,
             verbosity: FlooterShowVerbosity
             ) -> None:

        self.logger.writeln(f"Executed at: {storage.meta['created']}")

        for testset_name, endpoints in storage.meta['testsets'].items():
            for endpoint_name, requests in endpoints.items():
                for request_id, info in requests.items():
                    self.logger.it(bold(f'{name} > {testset_name} > {endpoint_name} > {request_id}'))

                    if verbosity >= FlooterShowVerbosity.HEADER:
                        self.logger.response(storage.load(request_id), info['parameters'],
                                             brief = verbosity == FlooterShowVerbosity.HEADER
                                             )
                        self.logger.writeln('-'*40)


    @_exit_on_exception(FlooterError)
    def run(self,
            name: str,  # rid or main
            verbosity: FlooterShowVerbosity
            ):

        self.logger.begin()

        if 'main' in name.lower().strip():
            self.show(
                'main',
                self.spec.storages.main,
                verbosity
                )
        else:
            self.show(
                name,
                self.spec.storages.get_run_storage(name),
                verbosity
            )

        sys.exit(0)
