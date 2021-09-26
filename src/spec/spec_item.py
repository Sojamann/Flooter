import abc

from pathlib import Path
from typing import Dict

class SpecItem(abc.ABC):
    @abc.abstractclassmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'SpecItem':
        pass
