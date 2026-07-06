Feature: People records
  Mirrors random-server's people-router.feature. The "/v1/people" endpoint
  becomes the list_records tool with kind "people".

  Background:
    Given the MCP server is available

  Scenario: Listing people records
    When the "people" records are listed
    Then the result should be a list with at least one item
    And each item should have "type" and "first" properties
    And the "type" property of each item should be "people"
    And the "age" property of each item should be numeric
    And the "prefix" property of each item should be a non-empty string
    And the "first" property of each item should be a non-empty string
    And the "last" property of each item should be a non-empty string
    And the "birthday" property of each item should be a non-empty string
    And the "gender" property of each item should be a non-empty string
    And the "zip" property of each item should be a non-empty string
    And the "ssnFour" property of each item should be a non-empty string
    And the "phone" property of each item should be a non-empty string
    And the "email" property of each item should be a non-empty string
