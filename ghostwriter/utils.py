# Standard Libraries
from datetime import datetime, timedelta

# Django Imports
from django.conf import settings

# 3rd Party Libraries
import jwt


def jwt_encode(payload, context=None):
    """Encode a JWT token."""
    return jwt.encode(
        payload,
        settings.GRAPHQL_JWT["JWT_SECRET_KEY"],
        settings.GRAPHQL_JWT["JWT_ALGORITHM"],
    )


def jwt_decode(token, context=None):
    """Decode a JWT token."""
    return jwt.decode(
        token,
        settings.GRAPHQL_JWT["JWT_SECRET_KEY"],
        options={
            "verify_exp": settings.GRAPHQL_JWT["JWT_VERIFY_EXPIRATION"],
            "verify_aud": settings.GRAPHQL_JWT["JWT_AUDIENCE"],
            "verify_signature": settings.GRAPHQL_JWT["JWT_VERIFY"],
        },
        leeway=timedelta(seconds=0),
        audience=settings.GRAPHQL_JWT["JWT_AUDIENCE"],
        issuer=None,
        algorithms=[settings.GRAPHQL_JWT["JWT_ALGORITHM"]],
    )


def generate_jwt_token(user, context=None):
    """Generate a JWT token for the user."""
    allowed_roles = [user.role]
    if user.is_superuser:
        allowed_roles.append("manager")

    jwt_iat = datetime.utcnow()
    jwt_datetime = jwt_iat + settings.GRAPHQL_JWT["JWT_EXPIRATION_DELTA"]
    jwt_expires = int(jwt_datetime.timestamp())
    payload = {}
    payload["username"] = str(user.username)
    payload["sub"] = str(user.id)
    payload["sub_name"] = user.username
    payload["sub_email"] = user.email
    payload["aud"] = settings.GRAPHQL_JWT["JWT_AUDIENCE"]
    payload["iat"] = jwt_iat
    payload["exp"] = jwt_expires
    payload["https://hasura.io/jwt/claims"] = {}
    payload["https://hasura.io/jwt/claims"]["x-hasura-allowed-roles"] = allowed_roles
    payload["https://hasura.io/jwt/claims"][
        "x-hasura-default-role"
    ] = user.role
    payload["https://hasura.io/jwt/claims"]["x-hasura-user-id"] = str(user.id)
    payload["https://hasura.io/jwt/claims"]["x-hasura-user-name"] = str(user.username)

    return payload, jwt_encode(payload)


def generate_hasura_error_payload(error_message, error_code):
    """Generate a standard error payload for Hasura."""
    return {
        "message": error_message,
        "extensions": {"code": error_code, },
    }


def verify_graphql_request(headers):
    """Verify that the request is a valid GraphQL request."""
    if headers.get("Action-Secret") is None:
        return False
    else:
        if headers["Action-Secret"] == settings.HASURA_ACTION_SECRET:
            return True
        return False
