Feature: Counting records
  Mirrors random-server's "/v1/<kind>/count" route via the count_records tool.

  Background:
    Given the MCP server is available

  Scenario: Counting people returns the configured pool size
    When the "people" records are counted
    Then the count should equal the configured pool size

  Scenario: The empty kind has no records
    When the "empty" records are counted
    Then the count should be 0
