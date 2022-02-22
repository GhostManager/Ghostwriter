# 3rd Party Libraries
import graphene
import graphql_jwt

# Ghostwriter Libraries
from ghostwriter.users import schema


class Mutation(schema.Mutation, graphene.ObjectType):
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    pass


class Query(schema.Query, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
