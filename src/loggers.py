import sys
import requests
from abc import abstractmethod

from typing import Any, Dict, Iterable, List, Tuple, Union

from termcolor import colored

# http://www.patorjk.com/software/taag/#p=display&f=Slant&t=Flooter
BANNER = """
############################################
##     ________            __             ##
##    / ____/ /___  ____  / /____  _____  ##
##   / /_  / / __ \/ __ \/ __/ _ \/ ___/  ##
##  / __/ / / /_/ / /_/ / /_/  __/ /      ##
## /_/   /_/\____/\____/\__/\___/_/       ##
##                                        ##
############################################

"""

def indent(value: Union[str, Iterable[str]]) -> Iterable[str]:
    if isinstance(value, str):
        value = [value]
    for item in value:
        yield f'\t{item}'

def bold(value: Union[str, Iterable[str]]) ->Iterable[str]:
    if isinstance(value, str):
        value = [value]
    for item in value:
        yield colored(item, attrs=['bold'])

def underline(value: Union[str, Iterable[str]]) ->Iterable[str]:
    if isinstance(value, str):
        value = [value]
    for item in value:
        yield colored(item, attrs=['underline'])

def color(value: Union[str, Iterable[str]], color: str) ->Iterable[str]:
    if isinstance(value, str):
        value = [value]
    for item in value:
        yield colored(item, color=color)

def iterable(value: Iterable[Any], prefix='- ', item_fmt_func = lambda x: str(x)) -> Iterable[str]:
    for item in value:
        yield f'{prefix}{item_fmt_func(item)}'

def key_value(value: Union[Tuple[str, str], Iterable[Tuple[str, str]]]) -> Iterable[str]:
    if isinstance(value, Tuple):
        value = [value]
    return iterable(value, prefix='', item_fmt_func= lambda k_v: f'{k_v[0]}: {k_v[1]}')

class Logger:
    def __init__(self, no_banner=False):
        self.no_banner = no_banner

    def begin(self):
        if not self.no_banner:
            self.write(BANNER)

    @abstractmethod
    def write(self, msg: str, attrs: List[str] = []):
        pass
    @abstractmethod
    def writeln(self, msg: str, attrs: List[str] = []):
        pass
    @abstractmethod
    def it(self, iterable: Iterable[str]):
        pass
    @abstractmethod
    def warn(self, msg: str):
        pass

    def response(self, resp: requests.Response, parameters: List[Tuple[str, str]], brief: bool = False) -> None:
        self.writeln('PARAMETERS' + '-'*40)
        self.it(indent(key_value(parameters)))
        self.writeln('-'*(40 + len('PARAMETERS')))


        kvs = [
            ('Url',             resp.url),
            ('Status',          resp.status_code),
            ('Reason',          resp.reason),
            ('Date',            resp.headers.get('Date', '')),
            ('Server',          resp.headers.get('Server', '')),
            ('Connection',      resp.headers.get('Connection', '')),
            ('Content-Type',    resp.headers.get('Content-Type', '')),
        ]

        self.writeln('HEADER' + '-'*40)
        self.it(indent(key_value(kvs)))
        self.writeln('-'*(40 + len('HEADER')))

        # print body only when not brief
        if not brief:
            self.writeln('BODY' + '-'*40)

            content_type = resp.headers.get('Content-Type', '')
            if 'json' in content_type:
                self.writeln(resp.json())
            elif 'zip' in content_type:
                self.writeln('<<ZIP FILE>>')
            else:
                self.writeln(resp.content.decode('utf-8'))

            self.writeln('-'*(40 + len('BODY')))


    def table(self, columns: List[str], rows: List[Dict[str, List[str]]]):
        """
        combination1: {
            application: 1, 2
            limit: 1000
        }
        rows is a list of multiValue Dicts
        """

        # rewrite rows to be presentable, multimap to single one
        rows = [dict({k: ', '.join(v) for k, v in row.items()}) for row in rows]

        # find largetst entry for every column
        column_lengths = list(map(lambda col: max(len(col), max(map(len, map(lambda row: row[col], rows)))), columns))

        sperator = '-'*(sum(column_lengths) + (len(columns) * 3) + 3)
        header_fmt = '||' + '|'.join(map(lambda cl: ' {:^' + str(cl) + '} ', column_lengths)) + '||'
        row_fmt = '||' + '|'.join(map(lambda col_w_len: ' {'+col_w_len[0]+':^' + str(col_w_len[1]) + '} ',  zip(columns, column_lengths))) + '||'

        self.writeln(sperator)
        self.writeln(header_fmt.format(*columns))
        self.writeln(sperator)

        for row in rows:
            self.writeln(row_fmt.format(**row))

        self.writeln(sperator)

class StdoutLogger(Logger):
    def __init__(self, no_banner: bool = False):
        super().__init__(no_banner = no_banner)
    def write(self, msg, attrs: List[str] = []):
        sys.stdout.write(colored(msg, attrs=attrs))

    def writeln(self, msg, attrs: List[str] = []):
        self.write(msg, attrs)
        sys.stdout.write('\n')

    def it(self, iterable: Iterable[str]):
        for item in iterable:
            self.writeln(item)

    def warn(self, msg: str):
        self.writeln(colored(msg, color='yellow'))

class NullLogger(Logger):
    def __init__(self, no_banner: bool = False):
        super().__init__(no_banner = no_banner)
    def write(self, msg, attrs: List[str] = []):
        pass
    def writeln(self, msg, attrs: List[str] = []):
        pass
    def it(self, iterable: Iterable[str]):
        pass
    def warn(self, msg: str):
        pass

