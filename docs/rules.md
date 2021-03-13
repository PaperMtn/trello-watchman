# Rules
Trello Watchman uses rules to provide the search terms to query Trello and Regex patterns to filter out true positives.

They are written in YAML, and follow this format:
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

Rules are stored in the directory watchman/rules, so you can see examples there.

**Scope**
This is what Trello should look for: text or attachments. You can also use both, with each on its own line

**Test cases**
These test cases are used to check that the regex pattern works. Each rule should have at least one match (pass) and one fail case.

If you want to return all results found by a query, enter the value `blank` for both cases. For example, when you are searching for all files. (See `word_files.yaml` for an example)

## Creating your own rules
You can easily create your own rules for Trello Watchman. The two most important parts are the search queries and the regex pattern.

### Search queries
These are stored as the entries in the 'strings' section of the rule, and are the search terms used to query Trello
 to find results.

Multiple entries can be put under strings to find as many potential hits as you can. So if I wanted to find social security numbers, I might use both of these search terms:
`- ssn`
`- social security`


### Regex pattern
This pattern is used to filter results that are returned by the search query.

If you want to return all results found by a query, enter the value `''` for the pattern. For example, when you are searching for all files. (See `word_files.yaml` for an example)
