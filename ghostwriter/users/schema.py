# Django Imports
from django.contrib.auth import get_user_model

# 3rd Party Libraries
import graphene
from graphene_django import DjangoObjectType
from graphql_jwt.shortcuts import create_refresh_token, get_token


# Make models available to graphene.Field
class UserType(DjangoObjectType):
    class Meta:
        model = get_user_model()


class CreateUser(graphene.Mutation):
    user = graphene.Field(UserType)
    token = graphene.String()
    refresh_token = graphene.String()

    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)
        email = graphene.String(required=True)

    def mutate(self, info, username, password, email):
        user = get_user_model()(
            username=username,
            email=email,
        )
        user.set_password(password)
        user.save()

        token = get_token(user)
        refresh_token = create_refresh_token(user)

        return CreateUser(
            user=user, token=token, refresh_token=refresh_token
        )


# Finalize creating mutation for schema
class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()


class Query(graphene.ObjectType):
    whoami = graphene.Field(UserType)
    users = graphene.List(UserType)

    def resolve_whoami(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Authentication Failure: Your must be signed in")
        return user

    def resolve_users(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise Exception("Authentication Failure: Your must be signed in")
        if user.userprofile.role != "manager":
            raise Exception("Authentication Failure: Must be Manager")
        return get_user_model().objects.all()
