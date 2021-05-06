import os
import re
import builtins
import calendar
import requests
import time
import yaml
import simplejson as json
from collections import namedtuple
from requests.exceptions import HTTPError
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter

from trello_watchman import logger
from trello_watchman import rule

TEXT_RESULT = namedtuple('TextResult', ('card_id', 'last_activity', 'title', 'description', 'url',
                                        'match_string', 'board'))

ATTACHMENT_RESULT = namedtuple('AttachmentResult', ('card_id', 'last_activity', 'title', 'description', 'url',
                                                    'attachments', 'board'))

BOARD = namedtuple('Board', ('id', 'name', 'description', 'closed', 'url', 'members'))

MEMBER = namedtuple('Member', ('id', 'username'))

ATTACHMENT = namedtuple('Attachment', ('id', 'name', 'uploaded', 'filename', 'url'))


class TrelloAPI(object):
    """Class that handles API connections to Trello and allows various requests

    Attributes:
        key: Trello API OAuth key
        token: Trello OAuth token
        base_url: Base level URL for the Trello API
        session: Requests session object
    """

    def __init__(self, key: str, token: str):
        """Inits DigitalShadowsAPI with base URL and required API arguments.
        Creates a requests session, mounts it and auths it.

        Args:
            key: Trello API OAuth key
            token: Trello API OAuth token
        """

        self.key = key
        self.token = token
        self.base_url = 'https://api.trello.com'
        self.session = session = requests.session()
        session.mount(self.base_url, HTTPAdapter(max_retries=Retry(connect=3, backoff_factor=1)))
        session.headers.update({'Authorization': f'OAuth oauth_consumer_key="{self.key}", oauth_token="{self.token}"'})
        session.params.update({
            'cards_limit': 1000,
            'card_members': 'true',
            'card_attachments': 'true',
            'members_limit': 100,
            'boards_limit': 1000,
            'board': 'true',
            'modelTypes': ['cards', 'boards'],
        })

    def _make_request(self,
                      url: str,
                      params: dict or str = None,
                      data: dict or str = None,
                      method: str = 'GET',
                      verify_ssl: bool = True) -> requests.Response:
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
        """Get Trello account information on the user the OAuth token
        is linked to

        Returns:
            JSON object containing Trello data for the user of the API token
        """

        return self._make_request('members/me').json()

    def get_card(self, card_id: str) -> json:
        """Get Trello card by ID

        Args:
            card_id: ID number for the Trello card to retrieve
        Returns:
            JSON object containing Trello card data
        """

        return self._make_request(f'cards/{card_id}').json()

    def get_card_actions(self, card_id: str) -> json:
        """Get actions carried out on a card by ID

        Args:
            card_id: ID number for the Trello card to retrieve actions for
        Returns:
            JSON object containing Trello card actions data
        """

        return self._make_request(f'cards/{card_id}/actions').json()

    def get_board(self, board_id: str) -> json:
        """Get Trello board by ID

        Args:
            board_id: ID number for the Trello board to retrieve
        Returns:
            JSON object containing Trello board data
        """

        return self._make_request(f'boards/{board_id}').json()

    def get_board_members(self, board_id: str) -> json:
        """Get Trello board members by ID

        Args:
            board_id: ID number for the Trello board members to retrieve
        Returns:
            JSON object containing Trello board members data
        """

        return self._make_request(f'boards/{board_id}/members').json()

    def get_member(self, member_id: str) -> json:
        """Get Trello member by ID

        Args:
            member_id: ID number for the Trello member to retrieve
        Returns:
            JSON object containing Trello member data
        """

        return self._make_request(f'members/{member_id}').json()

    def search(self, query: str) -> json:
        """Search Trello for matches to the given query

        Args:
            query: String query to search across Trello for
        Returns:
            JSON object containing Trello search results
        """

        self.session.params.update({
            'query': query,
        })

        return self._make_request('search').json()


def initiate_trello_connection() -> TrelloAPI:
    """Checks for credentials in environment variables of .conf file.
    If present, creates a Trello API client object authed to those credentials

    Returns:
        Trello API object
    """

    try:
        secret = os.environ.get('TRELLO_WATCHMAN_SECRET')
    except KeyError:
        with open(f'{os.path.expanduser("~")}/watchman.conf') as yaml_file:
            config = yaml.safe_load(yaml_file)

        secret = config.get('trello_watchman').get('secret')

    try:
        key = os.environ.get('TRELLO_WATCHMAN_KEY')

    except KeyError:
        with open(f'{os.path.expanduser("~")}/watchman.conf') as yaml_file:
            config = yaml.safe_load(yaml_file)

        key = config.get('trello_watchman').get('key')

    return TrelloAPI(key, secret)


def deduplicate(input_list: list) -> list:
    """Removes duplicates where results are returned by multiple queries

    Args:
        input_list: list of dict results to remove duplicate entries from
    Returns:
        De-duplicated list of results
    """

    list_of_strings = [json.dumps(d) for d in input_list]
    list_of_strings = set(list_of_strings)
    deduped_list = [json.loads(s) for s in list_of_strings]
    return list({match.get('card_id'): match for match in reversed(deduped_list)}.values())


def convert_time(timestamp: str) -> int:
    """Convert ISO 8601 timestamp to epoch

    Args:
        timestamp: String timestamp in the format:
            %Y-%m-%dT%H:%M:%S.%f%z
    Returns:
        Integer with the converted Unix epoch timestamp in seconds
    """

    pattern = '%Y-%m-%dT%H:%M:%S.%f%z'
    return int(time.mktime(time.strptime(timestamp, pattern)))


def find_attachments(trello: TrelloAPI,
                     log_handler: logger.Logger,
                     rule: rule.Rule,
                     timeframe=calendar.timegm(time.gmtime()) + 1576800000) -> list:
    """ Search Trello for attachments in cards based on the given rule and timeframe

    Args:
        trello: TrelloAPI object with authed connection to Trello
        log_handler: Logger object for outputting results
        rule: Rule object containing what to search for
        timeframe: Time period to search back
    Returns:
        A list containing dict objects ready to be logged as JSON
    """

    results = []
    now = calendar.timegm(time.gmtime())

    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.strings:
        card_list = trello.search(query).get('cards')
        formatted_query = str(query).replace('"', '')
        print(f'{len(card_list)} cards found matching: {formatted_query}')
        for card in card_list:
            if card.get('attachments') and convert_time(card.get('dateLastActivity')) > (now - timeframe):
                board = trello.get_board(card.get('idBoard'))
                board_members = trello.get_board_members(card.get('idBoard'))

                members = []
                for member in board_members:
                    members.append(MEMBER(member.get('id'), member.get('username')))

                board_result = BOARD(board.get('id'),
                                     board.get('name'),
                                     board.get('desc'),
                                     board.get('closed'),
                                     board.get('url'),
                                     members)

                attachments = []
                for attachment in card.get('attachments'):
                    attachments.append(ATTACHMENT(attachment.get('id'),
                                                  attachment.get('date'),
                                                  attachment.get('name'),
                                                  attachment.get('fileName'),
                                                  attachment.get('url')))

                attachment_result = ATTACHMENT_RESULT(card.get('id'),
                                                      card.get('dateLastActivity'),
                                                      card.get('name'),
                                                      card.get('desc'),
                                                      card.get('url'),
                                                      attachments,
                                                      board_result)

                results.append(attachment_result)

    if results:
        results = deduplicate(results)
        print(f'{len(results)} total matches found after filtering')
        return results
    else:
        print('No matches found after filtering')


def find_text(trello: TrelloAPI,
              log_handler: logger.Logger,
              rule: rule.Rule,
              timeframe=calendar.timegm(time.gmtime()) + 1576800000):
    """ Search Trello for text in cards based on the given rule and timeframe

        Args:
            trello: TrelloAPI object with authed connection to Trello
            log_handler: Logger object for outputting results
            rule: Rule object containing what to search for
            timeframe: Time period to search back
        Returns:
            A list containing dict objects ready to be logged as JSON
    """

    results = []
    now = calendar.timegm(time.gmtime())

    if isinstance(log_handler, logger.StdoutLogger):
        print = log_handler.log_info
    else:
        print = builtins.print

    for query in rule.strings:
        card_list = trello.search(query).get('cards')
        formatted_query = str(query).replace('"', '')
        print(f'{len(card_list)} cards found matching: {formatted_query}')
        for card in card_list:
            if convert_time(card.get('dateLastActivity')) > (now - timeframe):
                board = trello.get_board(card.get('idBoard'))
                board_members = trello.get_board_members(card.get('idBoard'))
                actions = trello.get_card_actions(card.get('id'))
                r = re.compile(rule.pattern)
                if r.search(str(card.get('desc'))):
                    members = []
                    for member in board_members:
                        members.append(MEMBER(member.get('id'), member.get('username')))

                    board_result = BOARD(board.get('id'),
                                         board.get('name'),
                                         board.get('desc'),
                                         board.get('closed'),
                                         board.get('url'),
                                         members)

                    text_result = TEXT_RESULT(card.get('id'),
                                              card.get('dateLastActivity'),
                                              card.get('name'),
                                              card.get('desc'),
                                              card.get('url'),
                                              r.search(str(card.get('desc'))).group(0),
                                              board_result)

                    if r.search(str(card.get('desc'))) or r.search(str(card.get('name'))):
                        results.append(text_result)
                    else:
                        for entry in actions:
                            if r.search(str(entry.get('text'))):
                                results.append(text_result)
    if results:
        results = deduplicate(results)
        print(f'{len(results)} total matches found after filtering')
        return results
    else:
        print('No matches found after filtering')
