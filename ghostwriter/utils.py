# Standard Libraries
from datetime import datetime, timedelta

# Django Imports
from django.conf import settings

# 3rd Party Libraries
import jwt
from graphql_jwt.settings import jwt_settings


## JWT payload for Hasura
def jwt_payload(user, context=None):
    allowed_roles = [user.role]
    if user.is_superuser:
        allowed_roles.append("manager")

    jwt_datetime = datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA
    jwt_expires = int(jwt_datetime.timestamp())
    payload = {}
    payload["username"] = str(user.username)
    payload["sub"] = str(user.id)
    payload["sub_name"] = str(user.username)
    payload["sub_email"] = str(user.email)
    payload["exp"] = jwt_expires
    payload["https://hasura.io/jwt/claims"] = {}
    payload["https://hasura.io/jwt/claims"]["x-hasura-allowed-roles"] = allowed_roles
    payload["https://hasura.io/jwt/claims"][
        "x-hasura-default-role"
    ] = user.role
    payload["https://hasura.io/jwt/claims"]["x-hasura-user-id"] = str(user.id)
    payload["https://hasura.io/jwt/claims"]["x-hasura-user"] = str(user.username)
    return payload

def jwt_encode(payload, context=None):
    return jwt.encode(
        payload,
        settings.GRAPHQL_JWT["JWT_SECRET_KEY"],
        settings.GRAPHQL_JWT["JWT_ALGORITHM"],
    )

def jwt_decode(token, context=None):
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

    return jwt_encode(payload)
