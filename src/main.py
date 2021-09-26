import sys
import argparse
from argparse import ArgumentParser

from pathlib import Path
from typing import Callable, Type
from commands.flooter_show import FlooterShow, FlooterShowVerbosity
from errors import FlooterError

from util import _exit_on_exception
from spec.floot_spec import FlootSpec
from commands.flooter_cmp import FlooterCompare
from commands.flooter_rm import FlooterRm
from commands.flooter_accept import FlooterAccept
from commands.flooter_run import FlooterRun
from commands.flooter_list import FlooterList


from loggers import NullLogger, StdoutLogger, Logger
LOGGERS = {
    'stdout': StdoutLogger,
    'null': NullLogger
}

def file_path(p: str) -> Path:
    fpath = Path(p)
    if not fpath.exists():
        raise argparse.ArgumentError(f'The provided path >{p}< does not exist.')
    if not fpath.is_file():
        raise argparse.ArgumentError(f'The provided path >{p}< is not a regular file.')
    return fpath

def dir_path(p: str) -> Path:
    dpath = Path(p)
    dpath.mkdir(exist_ok=True, parents=True)
    return dpath

def add_run_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser('run', help='run help')
    parser.add_argument('--id-only', action='store_true')
    parser.set_defaults(
        func = lambda args: FlooterRun(
            FlootSpec.load_from_file(args.config),
            NullLogger() if args.id_only else StdoutLogger()
            ).run())

def add_list_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser('list', help='list help')
    parser.set_defaults(
        func = lambda args: FlooterList(FlootSpec.load_from_file(args.config), StdoutLogger()).run())

def add_rm_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser('rm', help='rm help')
    parser.add_argument('id', type=str, help='The id of the run to remove')
    parser.set_defaults(
        func = lambda args: FlooterRm(FlootSpec.load_from_file(args.config), StdoutLogger(no_banner=True)).run(args.id))

def add_compare_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser('cmp', help='cmp help')
    parser.add_argument('--brief', action='store_true')
    parser.add_argument('a', type=str, help='The id of the run to compare with [main/other run]')
    parser.add_argument('b', type=str, nargs='?', help='The id of the run to compare with')
    parser.set_defaults(
        func = lambda args: FlooterCompare(FlootSpec.load_from_file(args.config), StdoutLogger(), args.brief).run(args.a, args.b))

def add_accept_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser('accept', help='accept help')
    parser.add_argument('id', type=str, help='The id of the run to accept')
    parser.add_argument('request_id', type=str, nargs='?', help='The request id to accept')
    parser.set_defaults(
        func = lambda args: FlooterAccept(FlootSpec.load_from_file(args.config), StdoutLogger(no_banner=True)).run(args.id, args.request_id))

def add_show_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser('show', help='show help')
    parser.add_argument('id', type=str, help='The id of the run to show or "main"')
    parser.add_argument('--verbosity', type=FlooterShowVerbosity.from_arg_str, choices=list(FlooterShowVerbosity), default=FlooterShowVerbosity.BODY)
    parser.set_defaults(
        func = lambda args: FlooterShow(FlootSpec.load_from_file(args.config), StdoutLogger()).run(args.id, args.verbosity))


def main():
    parser = ArgumentParser('Floot')
    parser.set_defaults(func= lambda args: parser.print_help())
    parser.add_argument('--config',
                        type=file_path,
                        required=True)
    parser.add_argument('--debug',
                        action='store_true')

    subparsers = parser.add_subparsers(help='sub-command help')
    add_run_parser(subparsers)
    add_list_parser(subparsers)
    add_rm_parser(subparsers)
    add_compare_parser(subparsers)
    add_accept_parser(subparsers)
    add_show_parser(subparsers)

    args = parser.parse_args()

    # in debug profile, not expected exceptions are not intercepted
    if args.debug:
        args.func(args)
    # in productive profile, exceptions are caught and the code 2 is returned
    else:
        _exit_on_exception(Exception)(args.func)(args)
    # !!! Nothing after this !!!

if __name__ == '__main__':
    main()