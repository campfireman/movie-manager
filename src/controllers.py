import datetime
import logging
import os
import sys
from argparse import Namespace
from operator import itemgetter
from typing import List, Tuple

import imdb
import numpy as np
import pandas as pd
from fuzzywuzzy import process
from tqdm import tqdm

from src import errors, settings
from src.gui import CliGui as Gui
from src.models import MovieTableWrapper

ia = imdb.IMDb()
log = logging.getLogger(__name__)


def add_year_matching(master_table: MovieTableWrapper, matches: List[Tuple], title: str, year: int) -> List[Tuple]:
    new_matches = []
    for match in matches:
        match_year = master_table.data.loc[master_table.data['title']
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


def add_entry(table: MovieTableWrapper, title: str, year: int, is_interactive: bool) -> None:
    entry = pd.DataFrame(data=[[None]*len(table.data.columns)],
                         columns=table.data.columns, index=None)
    entry['title'] = title
    entry['year'] = year
    try:
        add_imdb_info(entry, is_interactive)
    except errors.NoImdbInfo:
        log.warning(f'No IMDB matches found for {entry["title"]}')
    table.add_data(entry)


def add_imdb_info(entry: pd.DataFrame, is_interactive: bool, add_canonical_title: bool = False) -> pd.DataFrame:
    if entry['imdb_id'] and not pd.isnull(entry['imdb_id']):
        search = ia.get_movie(entry['imdb_id'])
        if add_canonical_title:
            entry['title'] = search['canonical title']
        return entry

    search = ia.search_movie(entry['title'])
    if len(search) == 0:
        raise errors.NoImdbInfo

    for result in search:
        result['year'] = result.get('year', 0)
        if result['year'] == entry['year']:
            result['score'] = 100
        elif result['year'] - 1 == entry['year'] or result['year'] + 1 == entry['year']:
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
            f'Choose an IMDB entry for {entry["title"]}. If none matches choose 0.', 1, list(range(0, len(data) + 1)))
        if choice > 0:
            choice -= 1
            imdb_link = f'https://www.imdb.com/title/tt{search[choice].getID()}/'
            imdb_id = search[choice].getID()
            if add_canonical_title:
                entry['title'] = search[choice]['canonical title']
    else:
        if len(search) > 0:
            imdb_link = f'https://www.imdb.com/title/tt{search[0].getID()}/'
            imdb_id = search[0].getID()

    entry['imdb_link'] = imdb_link
    entry['imdb_id'] = imdb_id
    return entry


def merge_tables(args: Namespace) -> None:
    if args.interactive:
        log.info('Starting in interactive mode')
    else:
        log.warning('Not in interactive mode!')
        if not Gui.prompt_confirm('Do you want to continue?'):
            sys.exit(0)

    master_table = MovieTableWrapper.from_csv(args.master_table_path)
    supplementary_table = MovieTableWrapper.from_csv(
        args.supplementary_table_path)

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
    master_table.save(master_table_backup_path)

    # add non-duplicates from supplementary table to master table
    for _, row in tqdm(list(supplementary_table.data.iterrows())):
        matches = []
        matches = process.extract(
            row['title'],
            master_table.data['title'].to_list(),
            limit=settings.MATCH_LIST_LIMIT,
        )
        if matches:
            matches = add_year_matching(
                master_table, matches, row['title'], row['year'])
            selected_match = select_match(
                row['title'], matches, args.interactive)
            if selected_match:
                log.warning(
                    f'Not adding {row["title"]} because of {selected_match}')
                continue
            else:
                add_entry(
                    master_table, row['title'], row['year'], args.interactive)
        else:
            log.info(
                f'No matches found for {row["title"]}. Adding by default.')
            add_entry(
                master_table, row['title'], row['year'], args.interactive)

    log.info('Final table:\n' + str(master_table))
    log.info(f'Writing new table to: {args.master_table_path}')
    master_table.save(args.master_table_path)


def add_info(args: Namespace) -> None:
    if args.interactive:
        log.info('Starting in interactive mode')
    else:
        log.warning('Not in interactive mode!')
        if not Gui.prompt_confirm('Do you want to continue?'):
            sys.exit(0)

    table = MovieTableWrapper.from_csv(args.table_path)

    table.backup(args.table_path)

    # add non-duplicates from supplementary table to master table
    for i, row in tqdm(list(table.data.iterrows())):
        try:
            table.data.loc[i, :] = add_imdb_info(
                row, args.interactive, args.add_canonical_title)
        except errors.NoImdbInfo:
            log.warning(f'No IMDB matches found for {row["title"]}')

    table.save(args.table_path)
