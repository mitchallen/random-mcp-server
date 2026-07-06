Feature: Word records
  Mirrors random-server's word-router.feature.

  Background:
    Given the MCP server is available

  Scenario: Listing word records
    When the "words" records are listed
    Then the result should be a list with at least one item
    And each item should have "type" and "value" properties
    And the "type" property of each item should be "words"
    And the "value" property of each item should be a non-empty string
