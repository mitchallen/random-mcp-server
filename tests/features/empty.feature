Feature: Empty records
  Mirrors random-server's empty-router.feature — the "empty" kind always yields
  an empty list.

  Background:
    Given the MCP server is available

  Scenario: Listing empty records
    When the "empty" records are listed
    Then the result should be an empty list
