# Standard Libraries
import jwt

# 3rd Party Libraries
import environ
from fastmcp.server.auth import AccessToken, TokenVerifier

env = environ.Env()
JWT_SECRET_KEY = env("JWT_SECRET_KEY", default="secret")

class GhostwriterTokenVerifier(TokenVerifier):
    """Verify the token from Ghostwriter."""

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify the JWT token and return the access token."""
        print("Validating authentication token...")
        try:
            decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"], audience="Ghostwriter")
            return AccessToken(
                token=token,
                client_id=decoded.get("client_id", ""),
                scopes=decoded.get("scopes", ["user"]),
                expires_at=decoded.get("exp"),
            )
        except Exception as e:
            print(e)
            return None