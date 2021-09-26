import sys
import shutil

from typing import Optional

from commands.command import Command
from errors import FlooterError, FlooterRunError
from loggers import Logger
from spec.floot_spec import FlootSpec
from util import _set, _exit_on_exception

class FlooterAccept(Command):
    def __init__(self, spec: FlootSpec, _: Optional[Logger]) -> None:
        self.spec = spec

    def accept_run(self, rid: str) -> None:
        """ Just copies everyhing to the main_dir. This alo copies the .meta file """
        storage = self.spec.storages.get_run_storage(rid)

        # disable autosave, otherwise everything is overriden again
        self.spec.storages.main.meta.noautosave()

        shutil.copytree(storage.base_dir, self.spec.storages.main.base_dir, dirs_exist_ok=True)

    def accept_request(self, rid: str, req_id: str) -> None:
        """ Just copies request file. No need to modify .meta file """

        storage = self.spec.storages.get_run_storage(rid)

        # find req_id and copy the content over to main
        for testset_name, endpoints in storage.meta['testsets'].items():
            for endpoint_name, req_ids in endpoints.items():
                if req_id in req_ids:
                    _set(self.spec.storages.main.meta,
                         f'testsets.{testset_name}.{endpoint_name}.{req_id}',
                         req_ids[req_id]
                    )
                    break


        if not storage.exists(req_id):
            raise FlooterRunError(f'The request {req_id} does not exist for the run {rid}')

        shutil.copy(storage.path(req_id), self.spec.storages.main.path(req_id))

    @_exit_on_exception(FlooterError)
    def run(self, rid: str, req_id: Optional[str]):
        msg = 'Are you sure that you want to accept the entire run (y/n)?: '
        if req_id is not None:
            msg = f'Are you sure that you want to accept the request {req_id} (y/n)?: '

        while True:
            sys.stdout.write(msg)
            sys.stdout.flush()
            user_resp = sys.stdin.readline().strip().lower()

            if user_resp in ['y', 'n']:

                # stop if no
                if user_resp == 'n':
                    return

                if req_id is None:
                    self.accept_run(rid)
                else:
                    self.accept_request(rid, req_id)

                break

        sys.exit(0)