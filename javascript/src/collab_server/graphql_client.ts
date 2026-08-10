// Apollo's lib is commonjs and tsx doesn't see its exports, so work around it.
import * as apollo from "@apollo/client/core";
const { ApolloClient, createHttpLink, InMemoryCache } = apollo;

import { setContext } from "@apollo/client/link/context";
import { env } from "node:process";

const graphqlEngineHostname =
    env["HASURA_GRAPHQL_SERVER_HOSTNAME"] || "graphql_engine";

const defaultGraphqlUri =
    "http://" + graphqlEngineHostname + ":8080/v1/graphql";

/** Create a Hasura client that forwards the document-scoped collaboration JWT. */
export function createCollabGqlClient(token: string, uri = defaultGraphqlUri) {
    const httpLink = createHttpLink({ uri });
    const authLink = setContext((_, { headers }) => ({
        headers: {
            ...headers,
            "x-hasura-admin-secret": (env as any)[
                "HASURA_GRAPHQL_ADMIN_SECRET"
            ],
            Authorization: "Bearer " + token,
        },
    }));

    return new ApolloClient({
        link: authLink.concat(httpLink),
        cache: new InMemoryCache(),
        defaultOptions: {
            query: {
                fetchPolicy: "no-cache",
                errorPolicy: "all",
            },
            watchQuery: {
                fetchPolicy: "no-cache",
                errorPolicy: "all",
            },
        },
    });
}
