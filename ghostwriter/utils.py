# Standard Libraries
from datetime import datetime

# 3rd Party Libraries
import jwt
from graphql_jwt.settings import jwt_settings


## JWT payload for Hasura
def jwt_payload(user, context=None):
    jwt_datetime = datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA
    jwt_expires = int(jwt_datetime.timestamp())
    payload = {}
    payload["username"] = str(user.username)  # For library compatibility
    payload["sub"] = str(user.id)
    payload["sub_name"] = user.username
    payload["sub_email"] = user.email
    payload["exp"] = jwt_expires
    payload["https://hasura.io/jwt/claims"] = {}
    payload["https://hasura.io/jwt/claims"]["x-hasura-allowed-roles"] = [
        user.role
    ]
    payload["https://hasura.io/jwt/claims"][
        "x-hasura-default-role"
    ] = user.role
    payload["https://hasura.io/jwt/claims"]["x-hasura-user-id"] = str(user.id)
    return payload
