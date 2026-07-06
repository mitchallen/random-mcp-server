Feature: Coord records
  Mirrors random-server's coord-router.feature.

  Background:
    Given the MCP server is available

  Scenario: Listing coord records
    When the "coords" records are listed
    Then the result should be a list with at least one item
    And each item should have "type" and "latitude" properties
    And the "type" property of each item should be "coords"
    And the "latitude" property of each item should be numeric
    And the "longitude" property of each item should be numeric
