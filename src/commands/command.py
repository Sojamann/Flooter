import abc
from pathlib import Path
from typing import Optional

from loggers import Logger
from spec.floot_spec import FlootSpec

class Command:
    @abc.abstractmethod
    def __init__(self, spec: FlootSpec, logger: Optional[Logger]) -> None:
        pass
    @abc.abstractmethod
    def run(self, *args, **kwargs) -> None:
        """
        This function handles the entire command. Nothing will be invoked afterwards.
        Ideally should the command use sys.exit(0) at the end or sys.exit(1) if
        a problem occured which is a non exception case. Like a failed compare.
        """
        pass