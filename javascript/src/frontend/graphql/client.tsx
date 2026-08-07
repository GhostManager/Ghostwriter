import {
    ApolloClient,
    ApolloProvider,
    createHttpLink,
    InMemoryCache,
} from "@apollo/client";
import { setContext } from "@apollo/client/link/context";
import { useMemo } from "react";
import { getCollabToken } from "../collab_forms/token";

export default function PageGraphqlProvider(props: {
    children: React.ReactNode;
}) {
    const client = useMemo(() => {
        const path = document.getElementById("graphql-path")!.innerHTML;

        const httpLink = createHttpLink({
            uri: window.location.protocol + "//" + window.location.host + path,
        });
        const authLink = setContext(async (_, { headers }) => {
            const auth = await getCollabToken();
            return {
                headers: {
                    ...headers,
                    Authorization: "Bearer " + auth,
                },
            };
        });

        return new ApolloClient({
            link: authLink.concat(httpLink),
            cache: new InMemoryCache(),
        });
    }, []);

    return <ApolloProvider client={client}>{props.children}</ApolloProvider>;
}
