# MCP Server

Edit any files python files inside `mcp-server/` and you must run `./ghostwriter-cli containers restart --dev`.
A tool will only load the `prompts.yaml` file when it is called so editing this file does not require a container restart.

# Authentication

The MCP server uses the JWT from ghostwriter for authentication and is required when calling any MCP methods. This token is used when querying the graphql endpoint over the local docker network.

# Tools

## GenerateExecutiveSummaryTool

This tool will query the findings on a given report ID and provide a prompt to the LLM to generate a natural language response. When the tool is called it loads the `executive_summary_prompt` from `prompts.yaml` and places your findings into the `{findings}` variable