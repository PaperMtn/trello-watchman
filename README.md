<img src="https://i.imgur.com/k0bVKkM.png" width="550">

# Trello Watchman
![Python 2.7 and 3 compatible](https://img.shields.io/pypi/pyversions/trello-watchman)
![PyPI version](https://img.shields.io/pypi/v/trello-watchman.svg)
![License: MIT](https://img.shields.io/pypi/l/trello-watchman.svg)

Monitoring your Trello boards for sensitive information

## About Trello Watchman
Trello Watchman is an application that uses the Trello API to look for potentially sensitive data exposed in your public Trello boards.

### Features
Trello Watchman looks for:

- API Keys, Tokens & Service Accounts
  - AWS, Azure, GCP, Google API, Slack (keys & webhooks), Twitter, Facebook, GitHub
  - Generic Private keys
  - Access Tokens, Bearer Tokens, Client Secrets, Private Tokens
- Files
    - Certificate files
    - Potentially interesting/malicious/sensitive files (.docm, .xlsm, .zip etc.)
    - Executable files
- Personal Data
    - Leaked passwords
    - Passport numbers, Dates of birth, Social security numbers, National insurance numbers, Drivers licence numbers (UK), Individual Taxpayer Identification Number

#### Time based searching
You can run Trello Watchman to look for results going back as far as:
- 24 hours
- 7 days
- 30 days
- All time

This means after one deep scan, you can schedule Trello Watchman to run regularly and only return results from your chosen timeframe.

### Rules
Trello Watchman uses custom YAML rules to detect matches in Trello.

They follow this format:

```yaml
---
filename:
enabled: [true|false]
meta:
  name:
  author:
  date:
  description: #what the search should find
  severity: #rating out of 100
scope:
- #[text|attachments]
test_cases:
  match_cases:
  - #test case that should match the regex*
  fail_cases:
  - #test case that should not match the regex*
strings:
- #search query to use in Trello*
pattern: #Regex pattern to filter out false positives*
```
There are Python tests to ensure rules are formatted properly and that the Regex patterns work in the `tests` dir

More information about rules, and how you can add your own, is in the file `docs/rules.md`.

### Logging

Trello Watchman gives the following logging options:
- Stdout
- Log file
- TCP stream

Results are output in JSON format, perfect for ingesting into a SIEM or other log analysis platform.

For file and TCP stream logging, configuration options need to be passed via `.conf` file or environment variable. See the file `docs/logging.md` for instructions on how to set it up.

If no logging option is given, Trello Watchman defaults to Stdout logging.

## Requirements
### Trello API token
To run Trello Watchman, you will need a Trello API OAuth access token, which take the form of a `key` and a `secret`. You can generate these [here](https://trello.com/app-key).

**Note**: User tokens act on behalf of the user who generates them, so I would suggest you create this app and authorise it using a service account, otherwise the app will have access to your private Trello boards.

#### Providing token
Trello Watchman will first try to get the secret and key from the environment variables `TRELLO_WATCHMAN_SECRET` and `TRELLO_WATCHMAN_KEY`, if this fails it will load the token from .conf file (see below).

### .conf file
Configuration options can be passed in a file named `watchman.conf` which must be stored in your home directory. The file should follow the YAML format, and should look like below:
```yaml
trello_watchman:
  secret: abc123
  key: abc123
  logging:
    file_logging:
      path: /var/log/
    json_tcp:
      host: localhost
      port: 9020
```
Trello Watchman will look for this file at runtime, and use the configuration options from here. If you are not using the advanced logging features, leave them blank.

If you are having issues with your .conf file, run it through a YAML linter.

An example file is in `docs/example.conf`

## Installation
Install via pip

`python3 -m pip install trello-watchman`

## Usage
Trello Watchman will be installed as a global command, use as follows:
```
usage: trello-watchman [-h] --timeframe {d,w,m,a} [--output {file,stdout,stream}]
                   [--version] [--all] [--attachments] [--text]

Monitoring your Trello boards for sensitive information

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  --all                 Find everything
  --attachments         Search for attachments
  --text                Search text

required arguments:
  --timeframe {d,w,m,a}
                        How far back to search: d = 24 hours w = 7 days, m =
                        30 days, a = all time
  --output {file,stdout,stream}
                        Where to send results

  ```

You can run Trello Watchman to look for everything, and output to default CSV:

`trello-watchman --timeframe a --all`

## Other Watchman apps
You may be interested in some of the other apps in the Watchman family:
- [Slack Watchman](https://github.com/PaperMtn/slack-watchman)
- [GitLab Watchman](https://github.com/PaperMtn/gitlab-watchman)
- [GitHub Watchman](https://github.com/PaperMtn/github-watchman)

## License
The source code for this project is released under the [GNU General Public Licence](https://www.gnu.org/licenses/licenses.html#GPL). This project is not associated with Trello or Atlassian.
