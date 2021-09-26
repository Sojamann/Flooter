import datetime
import time
import dataclasses
import shutil
import pickle
import yaml

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from errors import FlooterRunError
from util import _get, _to_absolute_path
from spec.spec_item import SpecItem

def _dump(p: Path, content: Any):
    with open(p, 'wb') as f:
        pickle.dump(content, f)

def _load(p: Path):
    with open(p, 'rb') as f:
        return pickle.load(f)

def _dump_as_yaml(p: Path, content: Any):
    with open(p, 'wt') as f:
        yaml.dump(content, f)

def _load_from_yaml(p: Path):
    with open(p, 'rt') as f:
        return yaml.load(f, Loader=yaml.FullLoader)

class PersistedDict():
    def __init__(self, path: Path, autosave = True):
        self.path = path
        self.autosave = autosave

        self.props: Dict[str, Any] = dict({'created': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')})

        if self.path.is_file() and self.path.exists():
            self.props = _load_from_yaml(self.path)

    def noautosave(self) -> None:
        self.autosave = False

    def keys(self) -> Iterable[Any]:
        return self.props.keys()

    def values(self) -> Iterable[Any]:
        return self.props.values()

    def items(self) -> Iterable[Tuple[Any, Any]]:
        return self.props.items()

    def __getitem__(self, name: str):
        return self.props[name]

    def __setitem__(self, name: str, value: Any):
        self.props[name] = value

    def __contains__(self, name: str):
        return name in self.props

    def __del__(self):
        if self.autosave:
            self.path.parent.mkdir(exist_ok=True, parents=True)
            _dump_as_yaml(self.path, self.props)


class Storage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

        if not self.base_dir.is_dir():
            self.base_dir.mkdir(parents=True)

        self.meta = PersistedDict(Path(base_dir, '.meta'))

    def exists(self, name: str) -> bool:
        p = Path(self.base_dir, name)
        return p.exists() and p.is_file()

    def path(self, name: str) -> Path:
        return Path(self.base_dir, name)

    def load(self, name: str) -> Any:
        p = Path(self.base_dir, name)
        if not p.is_file():
            raise FlooterRunError(f'There is no request with the id {name}')
        return _load(p)

    def save(self, name: str, content: Any) -> None:
        p = Path(self.base_dir, name)
        _dump(p, content)

    def list_requests(self) -> List[str]:
        """ returns list of request ids """
        return list(filter(
            lambda p: not p.stem.startswith('.'),
            self.base_dir.iterdir()))

@dataclasses.dataclass
class Storages(SpecItem):
    main: Storage
    runs_dir: Path

    @classmethod
    def parse(cls, spec_path: Path, content: Dict, path: str) -> 'Storages':
        main_dir  = _to_absolute_path(spec_path, _get(content, f'{path}.main', T=str))
        runs_dir    = _to_absolute_path(spec_path, _get(content, f'{path}.runs', T=str))
        return Storages(
            main      = Storage(main_dir),
            runs_dir    = runs_dir,
        )

    def make_run_storage(self, rid: str) -> Storage:
        p = Path(self.runs_dir, rid)
        if p.is_dir():
            raise FlooterRunError(f'Tried to create run, but a run with the id {rid} exists already')
        return Storage(Path(self.runs_dir, rid))

    def get_run_storage(self, rid: str) -> Storage:
        p = Path(self.runs_dir, rid)
        if not p.is_dir():
            raise FlooterRunError(f'Tried to use storage of {rid} but it does not exist! '
                                   'You might want to use the "list" command.')
        return Storage(p)

    def list_runs(self) -> List[str]:
        return [p.name for p in self.runs_dir.iterdir()]

    def rm_run(self, rid):
        shutil.rmtree(Path(self.runs_dir, rid))
