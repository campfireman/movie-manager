from __future__ import annotations

import datetime
import logging
import os
from inspect import getmembers, isfunction
from typing import Dict, Iterable, List

import numpy as np
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
                header = [x.strip() for x in header]
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

    def backup(self, path: str) -> None:
        # TODO: Will fail on windows bc of basename not returning filename
        table_name = os.path.basename(path).split('.')[0]
        table_backup_filename = f'{table_name}_{datetime.datetime.now().isoformat()}.csv'
        table_backup_directory = os.path.join(os.path.dirname(
            path), settings.TABLE_BACKUP_DIRECTORY)
        if not os.path.exists(table_backup_directory):
            os.makedirs(table_backup_directory)
        table_backup_path = os.path.join(
            table_backup_directory, table_backup_filename)
        log.info(f'Copying {table_name} table to: {table_backup_path}')
        self.save(table_backup_path)

    def add_row(self, new_row: pd.DataFrame) -> None:
        row_to_add = {}
        for col in self.data.columns:
            if col in new_row:
                row_to_add[col] = [new_row[col]]
            else:
                row_to_add[col] = [np.nan]
        row_to_add = pd.DataFrame.from_dict(row_to_add)
        self.data = pd.concat([self.data, row_to_add], ignore_index=True)

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
            data.columns = map(str.strip, data.columns)
            no_rows = data.shape[0]
            for col in settings.OPTIONAL_COLUMNS:
                if col not in data:
                    data[col] = no_rows * ['']
            return cls(data)
