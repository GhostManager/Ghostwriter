# 3rd Party Libraries
from fastmcp import FastMCP, Context

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.graphql import graphql_request

class ReportedFindingResource:
    """Resource for a reported finding."""

    def __init__(self, mcp: FastMCP):
        """Initialize the ReportedFindingResource."""
        mcp.resource(name='reported_finding', uri="reportedfinding://{report_finding_id}")(self.report_finding_resource)

    async def report_finding_resource(
        self,
        report_finding_id: int,
        ctx: Context
    ) -> dict:
        """
        Get a finding on a report. If you want to get a finding from the library use the `finding://{finding_id}` resource.

        Args:
            finding_id (int): The ID of the report finding.

        Returns:
            dict: The report finding data.
        """
        await ctx.info(f'Getting reported finding with ID: {report_finding_id}')
        graphql_query = '''query GetReportedFinding($id: bigint!) {
            reportedFinding(where: {id: {_eq: $id}}) {
                title
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
        response = await graphql_request(graphql_query, ctx, variables={"id": report_finding_id})
        return response.get("data", {})