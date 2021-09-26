import sys
from typing import Optional

from commands.command import Command
from loggers import Logger
from spec.floot_spec import FlootSpec
from errors import FlooterError, FlooterRunError
from util import _exit_on_exception




class FlooterRm(Command):
    def __init__(self, spec: FlootSpec, _: Optional[Logger]) -> None:
        self.spec = spec

    @_exit_on_exception(FlooterError)
    def run(self, rid, *args, **kwargs):
        rids = self.spec.storages.list_runs()

        if rid not in rids:
            raise FlooterRunError(f'You attempted to delete run {rid}'
                                  'but it does not exist')


        while True:
            sys.stdout.write(f'Do you really want to delete run {rid} (y/n): ')
            sys.stdout.flush()
            user_resp = sys.stdin.readline().strip().lower()

            if user_resp not in ['y', 'n']:
                sys.stdout.write('Please type n or y\n')
                continue

            # remove if yes
            if user_resp == 'y':
                self.spec.storages.rm_run(rid)

            break

        sys.exit(0)

