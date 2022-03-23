# Standard Libraries
import logging
from datetime import datetime, timedelta

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model

# 3rd Party Libraries
import jwt

# Using __name__ resolves to ghostwriter.utils
logger = logging.getLogger(__name__)


User = get_user_model()


def get_jwt_token_from_request(request):
    """
    Fetch the JSON Web Token from a ``request`` object's ``META`` attribute. The
    token is in the ``Authorization`` header with the ``Bearer `` prefix.
    """
    return request.META.get("HTTP_AUTHORIZATION", " ").split(" ")[1]


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


def verify_hasura_claims(payload):
    """Verify that the JSON Web Token payload contains the required Hasura claims."""
    if "https://hasura.io/jwt/claims" in payload:
        if (
            "X-Hasura-Role" in payload["https://hasura.io/jwt/claims"]
            and "X-Hasura-User-Id" in payload["https://hasura.io/jwt/claims"]
            and "X-Hasura-User-Name" in payload["https://hasura.io/jwt/claims"]
        ):
            return True
    return False


def get_jwt_payload(token, context=None):
    """Attempt to decode and verify the JWT token and return the payload."""
    try:
        payload = jwt_decode(token, context)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError):
        payload = None
    return payload


def generate_jwt_token(user, exp=None, context=None):
    """
    Generate a JWT token for the user. The token will expire after the
    ``JWT_EXPIRATION_DELTA`` setting unless the ``exp`` parameter is set.

    **Parameters**

    ``user``
        The :model:`users.User` object for the token
    ``exp``
        The expiration timestamp for the token
    """
    jwt_iat = datetime.utcnow()
    if exp:
        jwt_expires = exp
    else:
        jwt_datetime = jwt_iat + settings.GRAPHQL_JWT["JWT_EXPIRATION_DELTA"]
        jwt_expires = int(jwt_datetime.timestamp())
    payload = {}
    # Add user data to the payload
    payload["username"] = str(user.username)
    payload["sub"] = str(user.id)
    payload["sub_name"] = user.username
    payload["sub_email"] = user.email
    # Add the JWT date and audience to the payload
    payload["aud"] = settings.GRAPHQL_JWT["JWT_AUDIENCE"]
    payload["iat"] = jwt_iat
    payload["exp"] = jwt_expires
    # Add custom Hasura claims
    payload["https://hasura.io/jwt/claims"] = {}
    payload["https://hasura.io/jwt/claims"]["X-Hasura-Role"] = user.role
    payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Id"] = str(user.id)
    payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Name"] = str(user.username)

    return payload, jwt_encode(payload)


def generate_hasura_error_payload(error_message, error_code):
    """
    Generate a standard error payload for Hasura.

    Ref: https://hasura.io/docs/latest/graphql/core/actions/action-handlers.html
    """
    return {
        "message": error_message,
        "extensions": {"code": error_code, },
    }


def verify_graphql_request(headers):
    """
    Verify that the request is a valid request from Hasura using the
    ``HASURA_ACTION_SECRET`` secret shared between Django and Hasura.
    """
    HASURA_ACTION_SECRET = headers.get("Hasura-Action-Secret")
    if HASURA_ACTION_SECRET is None:
        return False

    if HASURA_ACTION_SECRET == settings.HASURA_ACTION_SECRET:
        return True
    return False


def verify_jwt_user(user_id):
    """
    Verify that the :model:`users.User` attached to the JSON Web Token payload
    is still active.
    """
    try:
        user = User.objects.filter(id=user_id).first()
        if user.is_active:
            return True
        else:
            logger.warning("Attempt to login with a JWT for an inactive user: %s", user)
    except User.DoesNotExist:
        logger.warning("Received a valid JWT for a user that does not exist %s", user_id)

    return False
