import pathlib
import yaml
from collections import namedtuple


class Rule(object):
    """Class that handles loaded rule objects"""

    def __init__(self,
                 filename: str,
                 enabled: bool,
                 meta: namedtuple,
                 scope: list,
                 test_cases: namedtuple,
                 strings: str,
                 pattern: str):
        self.filename = filename
        self.enabled = enabled
        self.meta = meta
        self.scope = scope
        self.test_cases = test_cases
        self.strings = strings
        self.pattern = pattern

    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__!r})'

    def __str__(self):
        return ' '.join(f'{k}: {v!s}' for k, v in self.__dict__.items())


def load_from_yaml(rule_path: pathlib.PosixPath) -> Rule:
    """Load YAML file and return a Rule object

    Args:
        rule_path: Path of YAML file
    Returns:
        Definition object with fields populated from the YAML
        definition file
    """

    with open(rule_path) as yaml_file:
        yaml_import = yaml.safe_load(yaml_file)

        meta = namedtuple('meta', ['name', 'author', 'date', 'version', 'description', 'severity'])
        meta.name = yaml_import.get('meta').get('name')
        meta.author = yaml_import.get('meta').get('author')
        meta.date = yaml_import.get('meta').get('date')
        meta.version = yaml_import.get('meta').get('version')
        meta.description = yaml_import.get('meta').get('description')
        meta.severity = yaml_import.get('meta').get('severity')

        test_cases = namedtuple('test_cases', ['match_cases', 'fail_cases'])
        test_cases.match_cases = yaml_import.get('test_cases').get('match_cases')
        test_cases.match_cases = yaml_import.get('test_cases').get('fail_cases')

        rule = Rule(filename=yaml_import.get('filename'),
                    enabled=yaml_import.get('enabled'),
                    meta=meta,
                    scope=yaml_import.get('scope'),
                    test_cases=test_cases,
                    strings=yaml_import.get('strings'),
                    pattern=yaml_import.get('pattern'))
    return rule
