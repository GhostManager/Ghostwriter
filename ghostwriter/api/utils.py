# Standard Libraries
import logging
from datetime import datetime

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model

# 3rd Party Libraries
import jwt

# Ghostwriter Libraries
from ghostwriter.rolodex.models import ClientInvite, ProjectAssignment, ProjectInvite

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
        leeway=10,
        audience=settings.GRAPHQL_JWT["JWT_AUDIENCE"],
        issuer=None,
        algorithms=[settings.GRAPHQL_JWT["JWT_ALGORITHM"]],
    )


def jwt_decode_no_verification(token):
    """
    Decode a JWT token without verifying anything. Used for logs and trusted
    :model:`api:APIKey` entries.

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
        leeway=10,
        audience=settings.GRAPHQL_JWT["JWT_AUDIENCE"],
        issuer=None,
        algorithms=[settings.GRAPHQL_JWT["JWT_ALGORITHM"]],
    )


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
            logger.warning("%s error (%s) with this payload: %s", type(exception).__name__, exception, bad_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError) as verify_exception:
            logger.error("%s error with this payload: %s", verify_exception, token)
        payload = None
    return payload


def generate_jwt(user, exp=None):
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

    payload = {
        "sub": str(user.id),
        "sub_name": user.username,
        "sub_email": user.email,
        "aud": settings.GRAPHQL_JWT["JWT_AUDIENCE"],
        "iat": jwt_iat.timestamp(),
        "exp": jwt_expires,
    }

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
        "extensions": {
            "code": error_code,
        },
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


def verify_project_access(user, project):
    """
    Verify that the user has access to the project.

    **Parameters**

    ``user``
        The :model:`users.User` object
    ``project``
        The :model:`projects.Project` object
    """
    if user.role == "admin":
        return True

    if user.role == "manager":
        return True

    assignments = ProjectAssignment.objects.filter(operator=user, project=project)
    client_invites = ClientInvite.objects.filter(user=user, client=project.client)
    project_invites = ProjectInvite.objects.filter(user=user, project=project)
    if any([assignments, client_invites, project_invites]):
        return True
    return False


def get_user_from_token(token):
    """
    Get the user from the JWT token.

    **Parameters**

    ``token``
        Decoded JWT payload
    """
    user_obj = User.objects.get(id=token["sub"])
    return user_obj
