# Standard Libraries
import sys
import argparse

# 3rd Party Libraries
from fastmcp import FastMCP

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.resources.client import ClientResource
from ghostwriter_mcp_server.resources.finding import FindingResource
from ghostwriter_mcp_server.resources.reported_finding import ReportedFindingResource
from ghostwriter_mcp_server.tools.generate_executive_summary import GenerateExecutiveSummaryTool
from ghostwriter_mcp_server.utils.auth import GhostwriterTokenVerifier

def main() -> int:
    """Entry point for the Ghostwriter MCP server.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """

    parser = argparse.ArgumentParser(description='Ghostwriter MCP Server')
    parser.add_argument('--host', default='localhost', help='Host for the MCP server')
    parser.add_argument('--port', type=int, default=8000, help='Port for the MCP server')

    args = parser.parse_args()

    mcp = FastMCP(
        "Ghostwriter MCP Server",
        host=args.host,
        port=args.port,
        auth=GhostwriterTokenVerifier(),
    )

    # Resources
    ClientResource(mcp)
    FindingResource(mcp)
    ReportedFindingResource(mcp)

    # Tools
    GenerateExecutiveSummaryTool(mcp)

    try:
        print(f'Starting Ghostwriter MCP Server on {args.host}:{args.port}')
        mcp.run(transport="streamable-http")
        return 0
    except Exception as e:
        print(f'Error starting Ghostwriter MCP Server: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())