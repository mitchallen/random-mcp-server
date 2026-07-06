Feature: Value records
  Mirrors random-server's value-router.feature.

  Background:
    Given the MCP server is available

  Scenario: Listing value records
    When the "values" records are listed
    Then the result should be a list with at least one item
    And each item should have "type" and "value" properties
    And the "type" property of each item should be "values"
    And the "value" property of each item should be numeric
    And the "name" property of each item should be a non-empty string
