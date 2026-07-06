Feature: Server info
  Mirrors random-server's server.feature (the GET / smoke test), adapted to the
  server_info MCP tool.

  Background:
    Given the MCP server is available

  Scenario: server_info reports a version
    When the server_info tool is called
    Then the result should contain a "version" property
