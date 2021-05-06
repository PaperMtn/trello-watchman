import yaml
import os
import unittest
from pathlib import Path

from trello_watchman import rule

RULES_PATH = (Path(__file__).parent / 'rules').resolve()


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


def check_yaml(rule):
    try:
        yaml_rule = yaml.safe_load(rule)
    except:
        return False
    return True


class TestEmail(unittest.TestCase):
    def test_rule_format(self):
        """Check rules are properly formed YAML ready to be ingested"""

        for root, dirs, files in os.walk(RULES_PATH):
            for rule_file in files:
                rule_path = (Path(root) / rule_file).resolve()
                if rule_path.name.endswith('.yaml'):
                    with open(rule_path) as yaml_file:
                        self.assertTrue(check_yaml(yaml_file.read()), msg=f'Malformed YAML: {yaml_file.name}')

    def test_rule_matching_cases(self):
        """Test that the match case strings match the regex. Skip if the match case is 'blank'"""

        rules_list = load_rules()
        for rule in rules_list:
            for test_case in rule.test_cases.match_cases:
                if not test_case == 'blank':
                    self.assertRegex(test_case, rule.pattern, msg='Regex does not detect given match case')

    def test_rule_failing_cases(self):
        """Test that the fail case strings don't match the regex. Skip if the fail case is 'blank'"""

        rules_list = load_rules()
        for rule in rules_list:
            for test_case in rule.test_cases.fail_cases:
                if not test_case == 'blank':
                    self.assertNotRegex(test_case, rule.pattern,
                                        msg='Regex does detect given failure case, it should '
                                            'not')


if __name__ == '__main__':
    unittest.main()
