import importlib.util
import sys

from typing import Iterable, List, Type, Any, Dict, Callable, Union
from types import ModuleType
from pathlib import Path

from errors import FlootSpecSyntaxError, FlooterError

def _exit_on_exception(ex: Type[Exception]):
    """
    Decorator that performs try, except
    """
    def _decorator(f: Callable) -> Callable:
        def _inner(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ex as err:
                sys.stderr.write(','.join(err.args))
                sys.stderr.write('\n')
                sys.exit(2 if isinstance(err, FlooterError) else 3)

        return _inner
    return _decorator


def _error_if_ukn(content: Dict, path: str, allowed: List) -> None:
    ukn = set(_get(content, path).keys()).difference(allowed)
    if len(ukn) != 0:
        raise FlootSpecSyntaxError(f'Found {ukn} in {path}. Only {allowed} are allowed')


def _merge(*dicts: List[Dict]) -> Dict:
    # copy and override
    n = dict(dicts[0])
    for other in dicts[1:]:
        if other is not None:
            n.update(other)
    return n


def _set(d: Dict[str, Union[Dict, Any]], path: str, value: str) -> None:
    """ the typing of d is only there to note that the value is either a child or a value """
    parts = path.split('.')

    # create all parents
    for part in parts[:-1]:
        if part not in d:
            d[part] = dict({})
        d = d[part]

    d[parts[-1]] = value

def _get(d: Dict, path: str, T: Type = None, choices: List[str]=None) -> Any:
    if len(path.strip()) == 0: return d

    for part in path.split('.'):
        if part not in d:
            raise FlooterError(f'Did not find {part} of path in {path}!')
        d = d[part]

    if T is not None and not isinstance(d, T):
        raise FlooterError(f'Expected {path} to be of type {T.__name__}')
    if choices is not None and d not in choices:
        raise FlooterError(f'Expected {path} to be one of {choices}')
    return d

def _get_or(d: Dict, path: str, default: Any = None, T: Type = None, choices: List[str]=None) -> Any:
    if len(path.strip()) == 0: return d

    parts = path.split('.')

    for part in parts[:-1]:
        if part not in d:
            raise FlooterError(f'Did not find {part} of path in {path}!')
        # everything in the path must be a dict
        if not isinstance(d[part], dict):
            raise FlooterError(f'Did not find {part} of path in {path}!')
        d = d[part]

    if parts[-1] not in d:
        return default

    val = d[parts[-1]]
    if T is not None and not isinstance(val, T):
        raise FlooterError(f'Expected {path} to be of type {T.__name__}')
    if choices is not None and val not in choices:
        raise FlooterError(f'Expected {path} to be one of {choices}')
    return d[parts[-1]]

def _box(before: Any, mid: Iterable, after: Any) -> Iterable:
    first = True
    for x in mid:
        if first:
            yield before
            first = False
        yield x

    # if there were items, first would be false
    if not first:
        yield after

def _call_if(content: Dict, path: str, f: Callable):
    """
    Calls f only if a given path exists in a dictionary
    """
    if _get_or(content, path) is not None:
        return f()

def _call_if_exists_or(content: Dict, path: str, if_case: Callable, else_case: Callable):
    if _get_or(content, path) is not None:
        return if_case()
    else:
        return else_case()

def _to_absolute_path(spec_path: Path, p: Union[Path, str]) -> Path:
    """
    Returns p if p is an absolute path, otherwise it will use the spec
    location as 'root' dir
    """
    if isinstance(p, str):
        p = Path(p)
    if p.is_absolute():
        return p
    return Path(spec_path.parent, p).absolute()

def _load_mod(mod_path: Path) -> ModuleType:
    """
    Load a python module from a file

    Example:
        mod = _load_mod('file.py')
        instance = mod.ClassName()
    """
    py_spec = importlib.util.spec_from_file_location('', mod_path)
    mod = importlib.util.module_from_spec(py_spec)
    py_spec.loader.exec_module(mod)
    return mod

def _coalesce_fns(*funcs: List[Callable], default=lambda *args, **kwargs: None):
    """
    Returns the function that is not None

    Example:
        _call_one(None, bad_var.print, sys.stdout.write)('Hello')
    """
    for f in funcs:
        if f is not None:
            return f

    return default


