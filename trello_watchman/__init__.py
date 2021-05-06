import calendar
import time
import argparse
import builtins
import os
import yaml
from pathlib import Path

from trello_watchman import __about__
from trello_watchman import trello_wrapper
from trello_watchman import logger
from trello_watchman import rule

DAY_TIMEFRAME = 86400
MONTH_TIMEFRAME = 2592000
WEEK_TIMEFRAME = 604800
ALL_TIME = calendar.timegm(time.gmtime()) + 1576800000

RULES_PATH = (Path(__file__).parent / 'rules').resolve()
OUTPUT_LOGGER = ''


def load_rules() -> list:
    """Load rules from YAML files

    Returns:
        List containing loaded definitions as Rule objects
    """

    loaded_definitions = []
    try:
        for root, dirs, files in os.walk(RULES_PATH):
            for rule_file in files:
                rule_path = (Path(root) / rule_file).resolve()
                if rule_path.name.endswith('.yaml'):
                    loaded_definitions.append(rule.load_from_yaml(rule_path))
        return loaded_definitions
    except Exception as e:
        raise e


def validate_conf(path: str) -> bool or list:
    """Check the file watchman.conf exists

    Args:
        path: Path where the conf file should be
    Returns:
        Either bool if environment variables have been set
        or True if the file watchman.conf file exists in the given path
    """

    if os.environ.get('TRELLO_WATCHMAN_SECRET') and os.environ.get('TRELLO_WATCHMAN_KEY'):
        return True
    if os.path.exists(path):
        with open(path) as yaml_file:
            return yaml.safe_load(yaml_file).get('trello_watchman')


def search(trello_conn: trello_wrapper.TrelloAPI, rule: rule.Rule, tf: int, scope: str):
    """Carries out a search on the Trello API based on the given rule,
     timeframe and scope

        Args:
            trello_conn: Trello API connection object to carry out the search
            rule: Rule object to use for the search
            tf: Epoch timeframe to search back in
            scope: What to search Trello for
        """

    if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
        print = OUTPUT_LOGGER.log_info
    else:
        print = builtins.print

    if scope == 'attachments':
        print(f'Searching for attachments containing {rule.meta.name}')
        attachments = trello_wrapper.find_attachments(trello_conn, OUTPUT_LOGGER, rule, tf)
        if attachments:
            for log_data in attachments:
                OUTPUT_LOGGER.log_notification(log_data, scope, rule.meta.name,
                                               rule.meta.severity)
    if scope == 'text':
        print(f'Searching for cards containing {rule.meta.name}')
        text = trello_wrapper.find_text(trello_conn, OUTPUT_LOGGER, rule, tf)
        if text:
            for log_data in text:
                OUTPUT_LOGGER.log_notification(log_data, scope, rule.meta.name,
                                               rule.meta.severity)


def main():
    global OUTPUT_LOGGER

    if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
        print = OUTPUT_LOGGER.log_critical
    else:
        print = builtins.print

    try:
        parser = argparse.ArgumentParser(description=__about__.__summary__)
        required = parser.add_argument_group('required arguments')
        required.add_argument('--timeframe', choices=['d', 'w', 'm', 'a'], dest='time',
                              help='How far back to search: d = 24 hours w = 7 days, m = 30 days, a = all time',
                              required=True)
        required.add_argument('--output', choices=['file', 'stdout', 'stream'], dest='logging_type',
                              help='Where to send results')
        parser.add_argument('--version', action='version',
                            version=f'trello-watchman {__about__.__version__}')
        parser.add_argument('--all', dest='everything', action='store_true',
                            help='Find everything')
        parser.add_argument('--attachments', dest='attachments', action='store_true',
                            help='Search for attachments')
        parser.add_argument('--text', dest='text', action='store_true',
                            help='Search text')

        args = parser.parse_args()
        tm = args.time
        everything = args.everything
        attachments = args.attachments
        text = args.text
        logging_type = args.logging_type

        if tm == 'd':
            tf = DAY_TIMEFRAME
        elif tm == 'w':
            tf = WEEK_TIMEFRAME
        elif tm == 'm':
            tf = MONTH_TIMEFRAME
        else:
            tf = ALL_TIME

        conf_path = f'{os.path.expanduser("~")}/watchman.conf'

        if not validate_conf(conf_path):
            raise Exception(f'TRELLO_WATCHMAN_SECRET/TRELLO_WATCHMAN_KEY environment variable or watchman.conf file '
                            f'not detected. \nEnsure environment variable is set or a valid file is located in your '
                            f'home directory: {os.path.expanduser("~")}')
        else:
            config = validate_conf(conf_path)
            connection = trello_wrapper.initiate_trello_connection()

        if logging_type:
            if logging_type == 'file':
                if os.environ.get('TRELLO_WATCHMAN_LOG_PATH'):
                    OUTPUT_LOGGER = logger.FileLogger(os.environ.get('TRELLO_WATCHMAN_LOG_PATH'))
                elif config.get('logging').get('file_logging').get('path') and \
                        os.path.exists(config.get('logging').get('file_logging').get('path')):
                    OUTPUT_LOGGER = logger.FileLogger(log_path=config.get('logging').get('file_logging').get('path'))
                else:
                    print('No config given, outputting trello_watchman.log file to home path')
                    OUTPUT_LOGGER = logger.FileLogger(log_path=os.path.expanduser('~'))
            elif logging_type == 'stdout':
                OUTPUT_LOGGER = logger.StdoutLogger()
            elif logging_type == 'stream':
                if os.environ.get('TRELLO_WATCHMAN_HOST') and os.environ.get('TRELLO_WATCHMAN_PORT'):
                    OUTPUT_LOGGER = logger.SocketJSONLogger(os.environ.get('TRELLO_WATCHMAN_HOST'),
                                                            os.environ.get('TRELLO_WATCHMAN_PORT'))
                elif config.get('logging').get('json_tcp').get('host') and \
                        config.get('logging').get('json_tcp').get('port'):
                    OUTPUT_LOGGER = logger.SocketJSONLogger(config.get('logging').get('json_tcp').get('host'),
                                                            config.get('logging').get('json_tcp').get('port'))
                else:
                    raise Exception("JSON TCP stream selected with no config")
        else:
            print('No logging option selected, defaulting to stdout')
            OUTPUT_LOGGER = logger.StdoutLogger()

        if not isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = builtins.print
            print('Trello Watchman')
            print(f'Version: {__about__.__version__}\n')
            print('Importing rules...')
            rules_list = load_rules()
            print(f'{len(rules_list)} rules loaded')
        else:
            OUTPUT_LOGGER.log_info(f'Trello Watchman started execution - Version: {__about__.__version__}')
            OUTPUT_LOGGER.log_info('Importing rules...')
            rules_list = load_rules()
            OUTPUT_LOGGER.log_info(f'{len(rules_list)} rules loaded')
            print = OUTPUT_LOGGER.log_info

        if everything:
            print('Getting everything...')
            for rule in rules_list:
                if 'attachments' in rule.scope:
                    search(connection, rule, tf, 'attachments')
                if 'text' in rule.scope:
                    search(connection, rule, tf, 'text')
        else:
            if attachments:
                print('Getting attachments')
                for rule in rules_list:
                    if 'attachments' in rule.scope:
                        search(connection, rule, tf, 'attachments')
            if text:
                print('Getting cards')
                for rule in rules_list:
                    if 'text' in rule.scope:
                        search(connection, rule, tf, 'text')

        print('++++++Audit completed++++++')

    except Exception as e:
        if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = OUTPUT_LOGGER.log_critical
        else:
            print = builtins.print

        print(e)


if __name__ == '__main__':
    main()
