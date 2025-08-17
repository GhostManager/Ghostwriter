# 3rd Party Libraries
from fastmcp import FastMCP, Context

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.graphql import graphql_request

class FindingResource:
    """Resource for a finding."""

    def __init__(self, mcp: FastMCP):
        """Initialize the FindingResource."""
        mcp.resource(name='finding', uri="finding://{finding_id}")(self.finding_resource)

    async def finding_resource(
        self,
        finding_id: int,
        ctx: Context
    ) -> dict:
        """
        Get a finding in the library. If you want to get a finding from a report use the `reportedfinding://{finding_id}` resource.

        Args:
            finding_id (int): The ID of the finding.

        Returns:
            dict: The finding data.
        """
        await ctx.info(f'Getting finding with ID: {finding_id}')
        graphql_query = '''query GetFinding($id: bigint!) {
            finding(where: {id: {_eq: $id}}) {
                title
                type {
                    findingType
                }
                severity {
                    severity
                }
                cvssScore
                cvssVector
                description
                replication_steps
                mitigation
                references
            }
        }'''
        response = await graphql_request(graphql_query, ctx, variables={"id": finding_id})
        return response.get("data", {})