# 3rd Party Libraries
from fastmcp import FastMCP, Context

# Ghostwriter MCP Server Imports
from ghostwriter_mcp_server.utils.graphql import graphql_request

class ClientResource:
    """Resource for a client."""

    def __init__(self, mcp: FastMCP):
        """Initialize the ClientResource."""
        mcp.resource(name='client', uri="client://{client_id}")(self.client_resource)

    async def client_resource(
        self,
        client_id: int,
        ctx: Context
    ) -> dict:
        """
        Get a client by its ID.

        Args:
            client_id (int): The ID of the client.

        Returns:
            dict: The client data.
        """
        await ctx.info(f'Getting client with ID: {client_id}')
        graphql_query = '''query GetClient($id: bigint!) {
            client(where: {id: {_eq: $id}}) {
                shortName
                codename
                timezone
                note
                address
            }
        }'''
        response = await graphql_request(graphql_query, ctx, variables={"id": client_id})
        return response.get("data", {})