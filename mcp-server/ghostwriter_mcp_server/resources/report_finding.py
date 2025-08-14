# 3rd Party Libraries
from mcp.server.fastmcp import Context, FastMCP

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.graphql import graphql_request

class ReportFindingResource:
    """Resource for a reported finding."""

    def __init__(self, mcp: FastMCP):
        """Initialize the ReportFindingResource."""
        mcp.resource(name='report_finding', uri="reportedFinding://{finding_id}")(self.report_finding_resource)

    async def report_finding_resource(
        self,
        finding_id: int,
        ctx: Context
    ) -> str:
        """Get a reported finding by its ID.
        Args:
            finding_id (int): The ID of the reported finding.
        Returns:
            dict: The reported finding data.
        """
        await ctx.info(f'Getting reported finding for ID {finding_id}')
        graphql_query = '''query GetReportedFinding($id: bigint!) {
            reportedFinding(where: {id: {_eq: $id}}) {
                title
                cweId
                cweName
                findingType {
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
        return await graphql_request(graphql_query, ctx, variables={"id": finding_id})
