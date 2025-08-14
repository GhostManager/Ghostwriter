# Standard Libraries
import httpx

# 3rd Party Libraries
import environ
from starlette.requests import Request
from mcp.server.fastmcp import Context

env = environ.Env()
GRAPHQL_URL = env("GRAPHQL_URL", default="http://localhost:8080")

async def graphql_request(query: str, context: Context, variables: dict = None) -> dict:
    """Helper function to make async GraphQL requests."""
    request: Request = context.request_context.request
    token = request.headers.get("Authorization")
    if not token:
        raise Exception("Unauthorized: No Authorization header found")
    headers = {"Content-Type": "application/json", "Authorization": token}
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers
        )
        response_json = response.json()
    if "errors" in response_json:
        raise Exception(f"GraphQL query failed with errors: {response_json['errors']}")
    else:
        return response_json