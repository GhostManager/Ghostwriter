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


def get_jwt_from_request(request):
    """
    Fetch the JSON Web Token from a ``request`` object's ``META`` attribute. The
    token is in the ``Authorization`` header with the ``Bearer `` prefix.

    **Parameters**

    ``request``
        Django ``request`` object
    """
    return request.META.get("HTTP_AUTHORIZATION", " ").split(" ")[1]


def jwt_encode(payload):
    """
    Encode a JWT token.

    **Parameters**

    ``payload``
        Plaintext JWT payload to be signed
    """
    return jwt.encode(
        payload,
        settings.GRAPHQL_JWT["JWT_SECRET_KEY"],
        settings.GRAPHQL_JWT["JWT_ALGORITHM"],
    )


def jwt_decode(token):
    """
    Decode a JWT token.

    **Parameters**

    ``token``
        Encoded JWT payload
    """
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


def jwt_decode_no_verification(token):
    """
    Decode a JWT token without verifying anything.

    **Parameters**

    ``token``
        Encoded JWT payload from ``generate_jwt``
    """
    return jwt.decode(
        token,
        settings.GRAPHQL_JWT["JWT_SECRET_KEY"],
        options={
            "verify_exp": False,
            "verify_aud": False,
            "verify_signature": False,
        },
        leeway=timedelta(seconds=0),
        audience=settings.GRAPHQL_JWT["JWT_AUDIENCE"],
        issuer=None,
        algorithms=[settings.GRAPHQL_JWT["JWT_ALGORITHM"]],
    )


def verify_hasura_claims(payload):
    """
    Verify that the JSON Web Token payload contains the required Hasura claims.

    **Parameters**

    ``token``
        Decoded JWT payload from ``get_jwt_payload``
    """
    if "https://hasura.io/jwt/claims" in payload:
        if (
            "X-Hasura-Role" in payload["https://hasura.io/jwt/claims"]
            and "X-Hasura-User-Id" in payload["https://hasura.io/jwt/claims"]
            and "X-Hasura-User-Name" in payload["https://hasura.io/jwt/claims"]
        ):
            return True
    return False


def get_jwt_payload(token):
    """
    Attempt to decode and verify the JWT token and return the payload.

    **Parameters**

    ``token``
        Encoded JWT payload to be decoded
    """
    try:
        payload = jwt_decode(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError) as exception:
        try:
            bad_token = jwt_decode_no_verification(token)
            logger.warning("%s error with this payload: %s", exception, bad_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError) as exception:
            logger.error("%s error with this payload: %s", exception, token)
        payload = None
    return payload


def generate_jwt(user, exp=None, exclude_hasura=False):
    """
    Generate a JWT token for the user. The token will expire after the
    ``JWT_EXPIRATION_DELTA`` setting unless the ``exp`` parameter is set.

    **Parameters**

    ``user``
        The :model:`users.User` object for the token
    ``exp``
        The expiration timestamp for the token
    ``exclude_hasura``
        If ``True``, the token will not contain the Hasura claims
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
    if not exclude_hasura:
        payload["https://hasura.io/jwt/claims"] = {}
        payload["https://hasura.io/jwt/claims"]["X-Hasura-Role"] = user.role
        payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Id"] = str(user.id)
        payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Name"] = str(user.username)

    return payload, jwt_encode(payload)


def generate_hasura_error_payload(error_message, error_code):
    """
    Generate a standard error payload for Hasura.

    Ref: https://hasura.io/docs/latest/graphql/core/actions/action-handlers.html

    **Parameters**

    ``error_message``
        Error message to be returned
    ``error_code``
        Error code to be returned
    """
    return {
        "message": error_message,
        "extensions": {"code": error_code, },
    }


def verify_graphql_request(headers):
    """
    Verify that the request is a valid request from Hasura using the
    ``HASURA_ACTION_SECRET`` secret shared between Django and Hasura.

    **Parameters**

    ``headers``
        Headers from a Django ``request`` object
    """
    HASURA_ACTION_SECRET = headers.get("Hasura-Action-Secret")
    if HASURA_ACTION_SECRET is None:
        return False

    if HASURA_ACTION_SECRET == settings.HASURA_ACTION_SECRET:
        return True
    return False


def verify_jwt_user(payload):
    """
    Verify that the :model:`users.User` attached to the JSON Web Token payload
    is still active.

    **Parameters**

    ``payload``
        Decoded JWT payload
    """
    try:
        role = payload["X-Hasura-Role"]
        user_id = payload["X-Hasura-User-Id"]
        username = payload["X-Hasura-User-Name"]

        user = User.objects.get(id=user_id)
        if (
            user.is_active
            and user.username == username
            and user.role == role
        ):
            return True
        else:
            logger.warning(
                "Suspicious login attempt with a valid JWT for user %s with mismatched user details: %s",
                user,
                payload
            )
    except User.DoesNotExist:
        logger.warning("Received a valid JWT for a user ID that does not exist: %s", user_id)

    return False
