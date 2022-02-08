import argparse
import logging

import coloredlogs

from src import controllers, settings

log = logging.getLogger(__name__)

coloredlogs.install(level=settings.LOG_LEVEL)


def main() -> int:
    parser = argparse.ArgumentParser(description='Manage your movie tables')
    parser.add_argument('--interactive', help='Ask before taking actions',
                        action='store_false', default=True)
    subparsers = parser.add_subparsers(dest='command')

    parser_merge = subparsers.add_parser(
        'merge', help='Merge a supplementary movie table into a master table')
    parser_merge.add_argument('master_table_path', type=str,
                              help='The path of the master table')
    parser_merge.add_argument('supplementary_table_path', type=str,
                              help='The path of the supplementary table to be merged into the master table')

    args = parser.parse_args()

    if (args.command == 'merge'):
        controllers.merge_tables(args)


if __name__ == '__main__':
    main()
