import sys

from commands.command import Command
from loggers import Logger, indent, bold, iterable
from spec.floot_spec import FlootSpec
from util import _exit_on_exception
from errors import FlooterError

class FlooterList(Command):
    def __init__(self, spec: FlootSpec, logger: Logger) -> None:
        self.spec = spec
        self.logger = logger

    @_exit_on_exception(FlooterError)
    def run(self, *args, **kwargs):
        self.logger.begin()

        ordered_runs = [(rid, self.spec.storages.get_run_storage(rid)) for rid in  self.spec.storages.list_runs()]
        ordered_runs.sort(key=lambda x: x[1].meta['created'])

        self.logger.it(bold('List of runs'))

        self.logger.it(indent(iterable(map(lambda x: x[0], ordered_runs))))

        sys.exit(0)
