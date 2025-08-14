# Standard Libraries
import sys
import argparse

# 3rd Party Libraries
import environ
from pydantic import AnyHttpUrl
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from loguru import logger

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.auth import GhostwriterTokenVerifier
# from ghostwriter_mcp_server.resources.report_finding import ReportFindingResource
from ghostwriter_mcp_server.tools.generate_executive_summary import GenerateExecutiveSummaryTool

def main() -> int:
    """Entry point for the Ghostwriter MCP server.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    env = environ.Env()
    FASTMCP_LOG_LEVEL = env("FASTMCP_LOG_LEVEL", default="WARNING")

    logger.remove()
    logger.add(sys.stderr, level=FASTMCP_LOG_LEVEL)

    parser = argparse.ArgumentParser(description='Ghostwriter MCP Server')
    parser.add_argument('--host', default='localhost', help='Host for the MCP server')
    parser.add_argument('--port', type=int, default=8000, help='Port for the MCP server')

    args = parser.parse_args()

    mcp = FastMCP(
        "Ghostwriter MCP Server",
        token_verifier=GhostwriterTokenVerifier(),
        host=args.host,
        port=args.port,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl("https://auth.example.com"),
            resource_server_url=AnyHttpUrl("http://localhost:3001"),
            required_scopes=["user"],
        ),
    )

    # ReportFindingResource(mcp)

    GenerateExecutiveSummaryTool(mcp)

    try:
        logger.info(f'Starting Ghostwriter MCP Server on {args.host}:{args.port}')
        mcp.run(transport="streamable-http")
        return 0
    except Exception as e:
        logger.error(f'Error starting Ghostwriter MCP Server: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())