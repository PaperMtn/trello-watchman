import os
import re
import builtins
import calendar
import requests
import time
import json
import yaml
from requests.exceptions import HTTPError
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter

from trello_watchman import config as cfg
from trello_watchman import logger


class TrelloAPI(object):
    def __init__(self, key, token):
        self.key = key
        self.token = token
        self.base_url = 'https://api.trello.com'
        self.session = session = requests.session()
        session.mount(self.base_url, HTTPAdapter(max_retries=Retry(connect=3, backoff_factor=1)))
        session.headers.update({'Authorization': 'OAuth oauth_consumer_key="{}", oauth_token="{}"'
                               .format(self.key, self.token)})
        session.params.update({
            'cards_limit': 1000,
            'card_members': 'true',
            'card_attachments': 'true',
            'members_limit': 100,
            'boards_limit': 1000,
            'board': 'true',
            'modelTypes': ['cards', 'boards'],
        })

    def make_request(self, url, params=None, data=None, method='GET', verify_ssl=True):
        try:
            relative_url = '/'.join((self.base_url, '1', url))
            response = self.session.request(method, relative_url, params=params, data=data, verify=verify_ssl)
            response.raise_for_status()

            return response

        except HTTPError as http_error:
            if response.status_code == 400:
                if response.text:
                    raise Exception(response.text)
                else:
                    raise http_error
            elif response.status_code == 429:
                print('Rate limit hit, cooling off...')
                time.sleep(90)
                response = self.session.request(method, relative_url, params=params, data=data, verify=verify_ssl)
                response.raise_for_status()

                return response
            else:
                raise http_error

        except Exception as e:
            print(e)

    def get_me(self):

        return self.make_request('members/me').json()

    def get_card(self, card_id):

        return self.make_request('cards/{}'.format(card_id)).json()

    def get_card_actions(self, card_id):

        return self.make_request('cards/{}/actions'.format(card_id)).json()

    def get_board(self, board_id):

        return self.make_request('boards/{}'.format(board_id)).json()

    def get_board_members(self, board_id):

        return self.make_request('boards/{}/members'.format(board_id)).json()

    def get_member(self, member_id):

        return self.make_request('members/{}'.format(member_id)).json()

    def search(self, query):

        self.session.params.update({
            'query': query,
        })

        return self.make_request('search').json()


def initiate_trello_connection():
    """Create a Trello API client object"""

    try:
        token = os.environ['TRELLO_WATCHMAN_SECRET']

    except KeyError:
        with open('{}/watchman.conf'.format(os.path.expanduser('~'))) as yaml_file:
            config = yaml.safe_load(yaml_file)

        token = config.get('trello_watchman').get('secret')
    try:
        key = os.environ['TRELLO_WATCHMAN_KEY']
    except KeyError:
        with open('{}/watchman.conf'.format(os.path.expanduser('~'))) as yaml_file:
            config = yaml.safe_load(yaml_file)

        token = config.get('trello_watchman').get('key')

    return TrelloAPI(key, token)


def deduplicate(input_list):
    """Removes duplicates where results are returned by multiple queries"""

    list_of_strings = [json.dumps(d) for d in input_list]
    list_of_strings = set(list_of_strings)
    deduped_list = [json.loads(s) for s in list_of_strings]
    return {match.get('card_id'): match for match in reversed(deduped_list)}.values()


def convert_time(timestamp):
    """Convert ISO 8601 timestamp to epoch """

    pattern = '%Y-%m-%dT%H:%M:%S.%f%z'
    return int(time.mktime(time.strptime(timestamp, pattern)))


def find_attachments(trello: TrelloAPI, log_handler, rule, timeframe=cfg.ALL_TIME):
    results = []
    now = calendar.timegm(time.gmtime())

    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.get('strings'):
        card_list = trello.search(query).get('cards')
        print('{} cards found matching: {}'.format(len(card_list), query.replace('"', '')))
        for card in card_list:
            if card.get('attachments') and convert_time(card.get('dateLastActivity')) > (now - timeframe):

                results_dict = {
                    'card_id': card.get('id'),
                    'last_activity': card.get('dateLastActivity'),
                    'title': card.get('name'),
                    'description': card.get('desc'),
                    'card_url': card.get('url'),
                }

                attachments = []
                for attachment in card.get('attachments'):
                    at_dict = {
                        'attachment_id': attachment.get('id'),
                        'attachment_uploaded': attachment.get('date'),
                        'attachment_name': attachment.get('name'),
                        'attachment_filename': attachment.get('fileName'),
                        'attachment_url': attachment.get('url')
                    }
                    attachments.append(at_dict)

                results_dict['attachments'] = attachments

                results.append(results_dict)

    if results:
        results = deduplicate(results)
        print('{} total matches found after filtering'.format(len(results)))
        return results
    else:
        print('No matches found after filtering')


def find_text(trello: TrelloAPI, log_handler, rule, timeframe=cfg.ALL_TIME):
    results = []
    now = calendar.timegm(time.gmtime())

    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.get('strings'):
        card_list = trello.search(query).get('cards')
        print('{} cards found matching: {}'.format(len(card_list), query.replace('"', '')))
        for card in card_list:
            if convert_time(card.get('dateLastActivity')) > (now - timeframe):
                board = trello.get_board(card.get('idBoard'))
                board_members = trello.get_board_members(card.get('idBoard'))
                actions = trello.get_card_actions(card.get('id'))
                r = re.compile(rule.get('pattern'))
                if r.search(str(card.get('desc'))):
                    members = []
                    for member in board_members:

                        member_dict = {
                            'id': member.get('id'),
                            'username': member.get('username')
                        }

                        members.append(member_dict)

                    results_dict = {
                        'card_id': card.get('id'),
                        'last_activity': card.get('dateLastActivity'),
                        'title': card.get('name'),
                        'description': card.get('desc'),
                        'card_url': card.get('url'),
                        'match_string': r.search(str(card.get('desc'))).group(0),
                        'board': {
                            'id': board.get('id'),
                            'name': board.get('name'),
                            'description': board.get('desc'),
                            'closed': board.get('closed'),
                            'url': board.get('url'),
                        }
                    }

                    results_dict['board']['members'] = members

                    if r.search(str(card.get('desc'))) or r.search(str(card.get('name'))):
                        results.append(results_dict)
                    else:
                        for entry in actions:
                            if r.search(str(entry.get('text'))):
                                results.append(results_dict)
    if results:
        results = deduplicate(results)
        print('{} total matches found after filtering'.format(len(results)))
        return results
    else:
        print('No matches found after filtering')
