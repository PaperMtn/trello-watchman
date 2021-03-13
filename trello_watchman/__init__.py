import argparse
import builtins
import os
import yaml
from pathlib import Path

from trello_watchman import config as cfg
from trello_watchman import __about__ as a
from trello_watchman import trello_wrapper as trello
from trello_watchman import logger

RULES_PATH = (Path(__file__).parent / 'rules').resolve()
OUTPUT_LOGGER = ''


def load_rules():
    """Import YAML rules"""

    rules = []
    try:
        for root, dirs, files in os.walk(RULES_PATH):
            for rule in files:
                rule_path = (Path(root) / rule).resolve()
                if rule_path.name.endswith('.yaml'):
                    with open(rule_path) as yaml_file:
                        rule = yaml.safe_load(yaml_file)
                        if rule.get('enabled'):
                            rules.append(rule)
        return rules
    except Exception as e:
        if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
            print = OUTPUT_LOGGER.log_critical
        else:
            print = builtins.print

        print(e)


def validate_conf(path):
    """Check the file watchman.conf exists"""

    if os.environ.get('TRELLO_WATCHMAN_SECRET') and os.environ.get('TRELLO_WATCHMAN_KEY'):
        return True
    if os.path.exists(path):
        with open(path) as yaml_file:
            return yaml.safe_load(yaml_file).get('trello_watchman')


def search(trello_conn, rule, tf, scope):
    if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
        print = OUTPUT_LOGGER.log_info
    else:
        print = builtins.print

    if scope == 'attachments':
        print('Searching for attachments containing {}'.format(rule.get('meta').get('name')))
        attachments = trello.find_attachments(trello_conn, OUTPUT_LOGGER, rule, tf)
        if attachments:
            for log_data in attachments:
                OUTPUT_LOGGER.log_notification(log_data, scope, rule.get('meta').get('name'),
                                               rule.get('meta').get('severity'))
    if scope == 'text':
        print('Searching for cards {}'.format(rule.get('meta').get('name')))
        text = trello.find_text(trello_conn, OUTPUT_LOGGER, rule, tf)
        if text:
            for log_data in text:
                OUTPUT_LOGGER.log_notification(log_data, scope, rule.get('meta').get('name'),
                                               rule.get('meta').get('severity'))


def main():
    global OUTPUT_LOGGER

    if isinstance(OUTPUT_LOGGER, logger.StdoutLogger):
        print = OUTPUT_LOGGER.log_critical
    else:
        print = builtins.print

    try:
        parser = argparse.ArgumentParser(description=a.__summary__)
        required = parser.add_argument_group('required arguments')
        required.add_argument('--timeframe', choices=['d', 'w', 'm', 'a'], dest='time',
                              help='How far back to search: d = 24 hours w = 7 days, m = 30 days, a = all time',
                              required=True)
        required.add_argument('--output', choices=['file', 'stdout', 'stream'], dest='logging_type',
                              help='Where to send results')
        parser.add_argument('--version', action='version',
                            version='trello-watchman {}'.format(a.__version__))
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
            tf = cfg.DAY_TIMEFRAME
        elif tm == 'w':
            tf = cfg.WEEK_TIMEFRAME
        elif tm == 'm':
            tf = cfg.MONTH_TIMEFRAME
        else:
            tf = cfg.ALL_TIME

        conf_path = '{}/watchman.conf'.format(os.path.expanduser('~'))

        if not validate_conf(conf_path):
            raise Exception(
                'TRELLO_WATCHMAN_SECRET/TRELLO_WATCHMAN_KEY environment variable or watchman.conf file not detected.'
                '\nEnsure environment variable is set or a valid file is located in your home '
                'directory: {} '.format(os.path.expanduser('~')))
        else:
            config = validate_conf(conf_path)
            connection = trello.initiate_trello_connection()

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
            print('Version: {}\n'.format(a.__version__))
            print('Importing rules...')
            rules_list = load_rules()
            print('{} rules loaded'.format(len(rules_list)))
        else:
            OUTPUT_LOGGER.log_info('Trello Watchman started execution - Version: {}'.format(a.__version__))
            OUTPUT_LOGGER.log_info('Importing rules...')
            rules_list = load_rules()
            OUTPUT_LOGGER.log_info('{} rules loaded'.format(len(rules_list)))
            print = OUTPUT_LOGGER.log_info

        if everything:
            print('Getting everything...')
            for rule in rules_list:
                if 'attachments' in rule.get('scope'):
                    search(connection, rule, tf, 'attachments')
                if 'text' in rule.get('scope'):
                    search(connection, rule, tf, 'text')
        else:
            if attachments:
                print('Getting attachments')
                for rule in rules_list:
                    if 'attachments' in rule.get('scope'):
                        search(connection, rule, tf, 'attachments')
            if text:
                print('Getting cards')
                for rule in rules_list:
                    if 'text' in rule.get('scope'):
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
