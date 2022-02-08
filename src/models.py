from __future__ import annotations

import logging
import os
from inspect import getmembers, isfunction
from typing import Dict, List

import pandas as pd

from src import settings

NL = '\n'

log = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


class TableValidator:
    def __init__(self, path: str):
        self.path = path

    def validate_file_path(self):
        if not os.path.exists(self.path):
            raise ValidationError('Table file does not exist')

        if os.path.isdir(self.path):
            raise ValidationError('Table file path is a directory')

    def validate_file_suffix(self):
        if not self.path.endswith('.csv'):
            raise ValidationError(
                'File does not end .csv, potentially no csv file')

    def validate_columns(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as table:
                header = table.readline().rstrip().lower().split(',')
                missing_columns = []
                for column in settings.REQUIRED_COLUMNS:
                    if column not in header:
                        missing_columns.append(column)
                if missing_columns:
                    raise ValidationError(
                        'Required columns do not exist: ' + ', '.join(missing_columns))

    def validate(self) -> List[ValidationError]:
        errors = []
        for func in getmembers(self.__class__, isfunction):
            if func[0].startswith('validate_'):
                try:
                    getattr(self, str(func[0]))()
                except ValidationError as e:
                    errors.append(e)
        return errors


class MovieTableWrapper:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def save(self, path: str) -> None:
        self.data.to_csv(path, index=None)
        return

    def add_data(self, new_data: Dict[List]) -> None:
        self.data = pd.concat([self.data, new_data], ignore_index=True)

    @classmethod
    def from_csv(cls, filepath: str) -> MovieTableWrapper:
        errors = TableValidator(filepath).validate()
        if errors:
            log.error(
                f'{filepath}: {NL}{NL.join(map(lambda x: str(x), errors))}')
            raise ValidationError('Given table is not valid. Cf. error log.')

        with open(filepath, 'r') as file:
            data = pd.read_csv(file, index_col=None)
            data.columns = map(str.lower, data.columns)
            return cls(data)
