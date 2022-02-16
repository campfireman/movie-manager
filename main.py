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
    parser_merge.add_argument('origin', type=str,
                              help='The name of the supplementary table to be noted as origin in the master table')

    parser_add_info = subparsers.add_parser(
        'addinfo', help='Add IMDB id and link to entries')
    parser_add_info.add_argument('table_path', type=str,
                                 help='The path of the table to be extended')
    parser_add_info.add_argument('--add_canonical_title', help='Replace title with canonical IMDB title',
                                 action='store_true', default=False)

    args = parser.parse_args()

    if (args.command == 'merge'):
        controllers.merge_tables(args)

    if (args.command == 'addinfo'):
        controllers.add_info(args)


if __name__ == '__main__':
    main()
