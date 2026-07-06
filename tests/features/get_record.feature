Feature: Getting a record by id
  Mirrors random-server's "/v1/<kind>/:id" route via the get_record tool, which
  uses 1-based ids and rejects out-of-range ids.

  Background:
    Given the MCP server is available

  Scenario: Fetching a record by id returns that kind
    When record 1 of "people" is fetched
    Then the fetched record should have "type" equal to "people"

  Scenario: The same id returns a stable record
    When record 1 of "coords" is fetched
    And record 1 of "coords" is fetched again
    Then both fetched records should be equal

  Scenario: An out-of-range id is rejected
    When record 9999 of "people" is fetched expecting an error
    Then an out-of-range error should be raised
