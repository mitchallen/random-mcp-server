Feature: Regenerating records
  The regenerate tool reseeds the pools, like restarting the REST server. A
  fixed seed makes the generated records reproducible.

  Background:
    Given the MCP server is available

  Scenario: Regenerate reports the seed it used
    When the records are regenerated with seed 7
    Then the result should contain a "seed" property
    And the "seed" property of the result should be 7

  Scenario: Regenerating with a fixed seed is reproducible
    When the records are regenerated with seed 42
    And record 1 of "people" is fetched
    And the records are regenerated with seed 42
    And record 1 of "people" is fetched again
    Then both fetched records should be equal
