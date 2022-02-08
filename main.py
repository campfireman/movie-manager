import argparse
import logging

import coloredlogs

from src import controllers

log = logging.getLogger(__name__)

coloredlogs.install(level='INFO')


def main() -> int:
    parser = argparse.ArgumentParser(description='Manage your movie tables')
    parser.add_argument('master_table_path', type=str,
                        help='The path of the master table')
    parser.add_argument('supplementary_table_path', type=str,
                        help='The path of the supplementary table to be merged into the master table')
    parser.add_argument('--interactive', help='Ask before taking actions',
                        action='store_false', default=True)
    args = parser.parse_args()

    controllers.merge_tables(args)


if __name__ == '__main__':
    main()
