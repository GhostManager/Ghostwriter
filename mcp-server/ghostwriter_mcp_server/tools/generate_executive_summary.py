# 3rd Party Libraries
from mcp.server.fastmcp import Context, FastMCP

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.graphql import graphql_request
from ghostwriter_mcp_server.utils.load_config import load_config

class GenerateExecutiveSummaryTool:
    """Tool to generate executive summaries for reports."""

    def __init__(self, mcp: FastMCP):
        """Initialize the GenerateExecutiveSummaryTool."""
        mcp.tool(name='generate_executive_summary')(self.generate_executive_summary_tool)

    async def generate_executive_summary_tool(
        self,
        ctx: Context,
        report_id: int
    ) -> str:
        """
        Generate an executive summary for a report.

        Args:
            report_id (int): The ID of the report to generate a summary for.

        Returns:
            str: A system prompt to generate an executive summary
        """
        await ctx.info(f'Loading the most up to date prompt template...')
        prompts = load_config("prompts.yaml")

        await ctx.info(f'Querying the findings for report {report_id}')
        graphql_query = '''query SearchReportFindings($reportId: bigint!) {
            reportedFinding(
                where: {
                    reportId: {_eq: $reportId},
                    severity: {severity: {_in: ["Critical", "High", "Medium", "Low", "Informational"]}}
                },
                order_by: {severity: {weight: asc}},
                limit: 5
            ) {
                title
                severity {
                    severity
                }
                description
                mitigation
            }
        }'''
        # Execute the GraphQL query
        response = await graphql_request(graphql_query, ctx, variables={"reportId": report_id})

        await ctx.info(f'Formatting the findings into a markdown string')
        findings_list = response.get("data", {}).get("reportedFinding", [])
        findings_str = "\n".join(
            f"# {f['title']} ({f['severity']['severity']})\n## Description\n{f['description']}\n## Recommendation\n{f['mitigation']}\n"
            for f in findings_list
        )

        if not findings_list:
            raise Exception("No findings found for the report.")

        await ctx.info(f'Generating the executive summary prompt')
        prompt_template = prompts['executive_summary_prompt']
        if "{findings}" not in prompt_template:
            raise Exception("The `executive_summary_prompt` prompt template must contain the {findings} variable")
        prompt = prompt_template.format(findings=findings_str)

        return prompt
