# 3rd Party Libraries
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import SamplingMessage, TextContent

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.graphql import graphql_request

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
            dict: The response from Ghostwriter containing a list of `reportedFinding` containing the title of the finding and the report name it was found on.
        """
        await ctx.info(f'Getting executive summary for report {report_id}')

        # Query the findings on the current report
        graphql_query = '''query SearchReportFindings($reportId: bigint!) {
            reportedFinding(
                where: {
                    reportId: {_eq: $reportId},
                    severity: {severity: {_in: ["Critical", "High", "Medium", "Low", "Informational"]}}
                },
                order_by: {severity: {weight: asc}}
            ) {
                title
                severity {
                    severity
                }
                description
                mitigation
            }
        }'''
        response = await graphql_request(graphql_query, ctx, variables={"reportId": report_id})

        # Format the response into markdown for the LLM to interpret
        findings = []
        for finding in response.get("data", {}).get("reportedFinding", []):
            title = finding["title"]
            severity = finding["severity"]["severity"]
            description = finding["description"]
            mitigation = finding["mitigation"]
            findings.append(f"# {title} ({severity})\n## Description\n{description}\n## Recommendation\n{mitigation}\n")
        findings_str = "\n".join(findings)

        # Send as a prompt to the LLM
        prompt = f"""You are a cybersecurity analyst tasked with generating an executive summary for a penetration test report. The summary should be concise, non-technical and it should be between 1 and 2 paragraphs, do not use bullet points.
        Use the findings provided between the <Findings> tags to:
        1. Summarize the overall security posture.
        2. Highlight the number and severity of findings (e.g., how many critical, high, medium, low, and informational issues were found).
        3. Mention the general nature of the vulnerabilities discovered (e.g., misconfigurations, outdated software, weak authentication).
        4. Emphasize the importance of remediation and outline a general prioritization strategy.
        5. Maintain a professional tone and avoid deep technical jargon.

        <Findings>
        {findings_str}
        </Findings>"""

        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt)
                )
            ],
            max_tokens=1000,
        )

        # Return the generated executive summary
        if result.content.type == "text":
            return result.content.text
        return str(result.content)
