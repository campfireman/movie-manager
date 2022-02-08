import logging
from email import header
from typing import Iterable, List

from tabulate import tabulate

log = logging.getLogger(__name__)


class CliGui:
    @staticmethod
    def prompt_confirm(message: str, default: bool = True) -> bool:
        selector = '[Y/n]' if default else '[y/N]'
        answer = input(f'{message} {selector} ').lower()
        if answer == 'y' or answer == 'yes' or (answer == '' and default):
            return True
        if answer == 'n' or answer == 'no' or (answer == '' and not default):
            return False
        return False

    @staticmethod
    def get_int_choice(message: str, default_index: int, choices: List[int]) -> int:
        choice = ''
        while type(choice) != int:
            choice = input(f'{message} [default: {choices[default_index]}]: ')
            if choice == '':
                return default_index
            try:
                choice = int(choice)
                return choice
            except ValueError as e:
                log.error(e)
                choice = ''

    @staticmethod
    def print_table(headers: List[str], data: List[Iterable], enumerate: bool = True):
        if enumerate:
            enumerated_data = []
            for i in range(1, len(data) + 1):
                enumerated_data.append((i,) + data[i - 1])
            data = enumerated_data
            headers = ['#'] + headers
        print(tabulate(data, headers=headers))
