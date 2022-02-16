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


def add_heuristic(master_table: MovieTableWrapper, matches: List[Tuple], title: str, year: int) -> List[Tuple]:
    new_matches = []
    for match in matches:
        # if no_matches < settings.MATCH_LIST_LIMIT rest is padded with pandas nan
        if pd.isnull(match[0]):
            continue

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


def add_entry(table: MovieTableWrapper, row, is_interactive: bool) -> None:
    try:
        add_imdb_info(row, is_interactive)
    except errors.NoImdbInfo:
        log.warning(f'No IMDB matches found for {row["title"]}')
    table.add_data(row)


def add_imdb_info(entry: pd.DataFrame, is_interactive: bool, add_canonical_title: bool = False) -> pd.DataFrame:
    if entry['imdb_id'] and not pd.isnull(entry['imdb_id']):
        search = ia.get_movie(entry['imdb_id'])
        if not search:
            log.warning(
                f'Could not find a match for {entry["imdb_id"]} on IMDB, potentially invalid ID. Skipping')
            return entry
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
    master_table.backup(args.master_table_path)

    # add non-duplicates from supplementary table to master table
    for _, row in tqdm(list(supplementary_table.data.iterrows())):
        id_match = master_table.data.loc[master_table.data['imdb_id']
                                         == row['imdb_id']]
        if not id_match.empty:
            if id_match.shape[0] > 1:
                log.warning(
                    f'Found more than one match for {row["title"]} with ID {row["imdb_id"]}')
            log.warning(
                f'Found matching ID for {row["title"]} ({row["imdb_id"]})')
            continue

        matches = []
        matches = process.extract(
            row['title'],
            master_table.data['title'].to_list(),
            limit=settings.MATCH_LIST_LIMIT,
        )
        if matches:
            matches = add_heuristic(
                master_table, matches, row['title'], row['year'])
            selected_match = select_match(
                row['title'], matches, args.interactive)
            if selected_match:
                log.warning(
                    f'Not adding {row["title"]} because of {selected_match}')
                continue
            else:
                add_entry(
                    master_table, row, args.interactive)
        else:
            log.info(
                f'No matches found for {row["title"]}. Adding by default.')
            add_entry(
                master_table, row, args.interactive)

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
