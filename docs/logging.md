# Logging
Trello Watchman gives the following logging options:
- Log file
- Stdout
- TCP stream

## JSON formatted logging
All other logging options output their logs in JSON format. Here is an example:

```json
{"localtime": "2021-03-09 00:00:00,000", "level": "NOTIFY", "source": "Trello Watchman", "scope": "text", "severity": "70", "detection_type": "Slack API Tokens", "detection_data": {"card_id": "600000000", "last_activity": "2021-03-09T00:00:00.000Z", "title": "Slack", "description": "API_KEY = xoxb-11111111111-a1a1a1a1a1a1a1a1a1a1a1a1", "card_url": "https://trello.com/...", "match_string": "xoxb-11111111111-a1a1a1a1a1a1a1a1a1a1a1a1", "board": {"id": "600000000", "name": "Westeros Board", "description": "", "closed": false, "url": "https://trello.com/...", "members": [{"id": "700000000", "username": "robertbaratheon"}]}}}
```

This should contain all of the information you require to ingest these logs into a SIEM, or other log analysis platform.


### File logging
File logging saves JSON formatted logs to a file.

The path where you want to output the file needs to be passed when running Trello Watchman. This can be done via the .conf file:
```yaml
trello_watchman:
  secret: abc123
  key: abc123
  logging:
    file_logging:
      path: /var/log/
    json_tcp:
      host: 
      port: 
```
Or by setting your log path in the environment variable: `TRELLO_WATCHMAN_LOG_PATH`

If file logging is selected as the output option, but no path is give, Trello Watchman defaults to the user's home directory.

The filename will be `trello_watchman.log`

Note: Trello Watchman does not handle the rotation of the file. You would need a solution such as logrotate for this.

### Stdout logging
Stdout logging sends JSON formatted logs to Stdout, for you to capture however you want.

### TCP stream logging
With this option, JSON formatted logs are sent to a destination of your choosing via TCP

You will need to pass Trello Watchman a host and port to receive the logs, either via .conf file:

```yaml
trello_watchman:
  secret: abc123
  key: abc123
  logging:
    file_logging:
      path: 
    json_tcp:
      host: localhost
      port: 9020
```
Or by setting the environment variables `TRELLO_WATCHMAN_HOST` and `TRELLO_WATCHMAN_PORT`
