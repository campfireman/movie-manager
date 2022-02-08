import argparse
import datetime
import logging
import os
import shutil
import sys
from doctest import master
from inspect import getmembers, isfunction
from io import BufferedReader
from operator import itemgetter
from typing import List, Tuple

import coloredlogs
import imdb
import pandas as pd
from fuzzywuzzy import process
from tqdm import tqdm

from src import settings
from src.gui import CliGui as Gui

NL = '\n'
ia = imdb.IMDb()

log = logging.getLogger(__name__)

coloredlogs.install(level='INFO')


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


def read_table(fp: BufferedReader) -> pd.DataFrame:
    table = pd.read_csv(fp, index_col=None)
    table.columns = map(str.lower, table.columns)
    return table


def add_year_matching(master_table: pd.DataFrame, supplementary_table: pd.DataFrame, matches: List[Tuple], title: str, year: int) -> List[Tuple]:
    new_matches = []
    for match in matches:
        match_year = master_table.loc[master_table['title']
                                      == match[0]]['year'].iloc[0]
        match_coeff = 0
        if match_year == year:
            match_coeff = 100
        elif match_year + 1 == year or match_year - 1 == year:
            match_coeff = 50
        coefficient = (match[1] + match_coeff) / 2
        new_matches.append((match[0], coefficient, match_coeff, match[1]))
    new_matches.sort(key=itemgetter(1), reverse=True)
    return new_matches


def select_match(title: str, matches: List[Tuple], is_interactive: bool) -> Tuple:
    if is_interactive:
        Gui.print_table(
            ['Title', 'Total match (%)', 'Year match (%)', 'Title match (%)'], matches)
        choice = Gui.get_int_choice(f'Choose a match for "{title}". If no match is correct type 0.', 0,
                                    list(range(0, len(matches) + 1)))
        if choice == 0:
            return None
        else:
            return matches[choice - 1]
    else:
        if matches[0][1] > settings.NON_INTERACTIVE_MATCH_THRESHOLD:
            return matches[0]
        else:
            return None


def add_entry(table: pd.DataFrame, title: str, year: int, is_interactive: bool) -> None:
    entry = pd.DataFrame(data=[[None]*len(table.columns)],
                         columns=table.columns, index=None)
    entry['title'] = title
    entry['year'] = year
    search = ia.search_movie(title)
    for result in search:
        result['year'] = result.get('year', 0)
        if result['year'] == year:
            result['score'] = 100
        elif result['year'] - 1 == year or result['year'] + 1 == year:
            result['score'] = 50
        else:
            result['score'] = 0
    search.sort(key=itemgetter('score'), reverse=True)
    imdb_link = ''
    imdb_id = ''
    if is_interactive:
        data = []
        for i, item in enumerate(search):
            data.append((item['title'], item['year'], item['score']))
            if i == settings.IMDB_LIST_LIMIT - 1:
                break
        Gui.print_table(['Title', 'Year', 'Score'], data)
        choice = Gui.get_int_choice(
            'Choose an IMDB entry. If none matches choose 0.', 1, list(range(0, len(data) + 1)))
        if choice > 0:
            choice -= 1
            imdb_link = f'https://www.imdb.com/title/tt{search[choice].getID()}/'
            imdb_id = search[choice].getID()

    else:
        if len(search) > 0:
            imdb_link = f'https://www.imdb.com/title/tt{search[0].getID()}/'
            imdb_id = search[0].getID()

    entry['imdb_link'] = f'{imdb_link}'
    entry['imdb_id'] = imdb_id
    return pd.concat([table, entry], ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Manage you movie tables')
    parser.add_argument('master_table_path', type=str,
                        help='The path of the master table')
    parser.add_argument('supplementary_table_path', type=str,
                        help='The path of the supplementary table to be merged into the master table')
    parser.add_argument('--interactive', help='Ask before taking actions',
                        action='store_false', default=True)
    args = parser.parse_args()

    if args.interactive:
        log.info('Starting in interactive mode')
    else:
        log.warning('Not in interactive mode!')
        if not Gui.prompt_confirm('Do you want to continue?'):
            sys.exit(0)

    # validate tables
    while errors := TableValidator(args.master_table_path).validate():
        log.error(
            f'Master table: {NL}{NL.join(map(lambda x: str(x), errors))}')
        args.master_table_path = input(
            'Please enter a new path for the master table: ')

    while errors := TableValidator(args.supplementary_table_path).validate():
        log.warning(
            f'Supplementary table: {NL}{NL.join(map(lambda x: str(x), errors))}')
        args.supplementary_table_path = input(
            'Please enter a new path for the supplementary table: ')

    # copy master table
    # TODO: Will fail on windows bc of basename not returning filename
    master_table_name = os.path.basename(args.master_table_path).split('.')[0]
    master_table_backup_filename = f'{master_table_name}_{datetime.datetime.now().isoformat()}.csv'
    master_table_backup_directory = os.path.join(os.path.dirname(
        args.master_table_path), settings.MASTER_TABLE_BACKUP_DIRECTORY)
    if not os.path.exists(master_table_backup_directory):
        os.makedirs(master_table_backup_directory)
    master_table_backup_path = os.path.join(
        master_table_backup_directory, master_table_backup_filename)
    log.info(f'Copying master table to: {master_table_backup_path}')
    shutil.copy(args.master_table_path, master_table_backup_path)

    # add non-duplicates from supplementary table to master table
    with open(args.master_table_path, 'r') as master_table_file, open(args.supplementary_table_path, 'r') as supplementary_table_file:
        master_table = read_table(master_table_file)
        supplementary_table = read_table(supplementary_table_file)
        for _, row in tqdm(list(supplementary_table.iterrows())):
            matches = []
            matches = process.extract(
                row['title'],
                master_table['title'].to_list(),
                limit=settings.MATCH_LIST_LIMIT,
            )
            if matches:
                matches = add_year_matching(
                    master_table, supplementary_table, matches, row['title'], row['year'])
                selected_match = select_match(
                    row['title'], matches, args.interactive)
                if selected_match:
                    log.warning(
                        f'Not adding {row["title"]} because of {selected_match}')
                    continue
                else:
                    master_table = add_entry(
                        master_table, row['title'], row['year'], args.interactive)
            else:
                log.info(
                    f'No matches found for {row["title"]}. Adding by default.')
                master_table = add_entry(
                    master_table, row['title'], row['year'], args.interactive)

    log.info('Final table:\n' + str(master_table))
    with open(args.master_table_path, 'w'):
        log.info(f'Writing new table to: {args.master_table_path}')
        master_table.to_csv(args.master_table_path, index=None)


if __name__ == '__main__':
    main()
