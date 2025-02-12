// Collaborative editing server, based on Hocuspocus
//
// Dynamically converts the standard models from the GraphQL API to/from YJS.
//
// Since documents are made dynamically, its helpful to ensure that the client doesn't
// receive a newly loaded yjs doc, otherwise it will try to merge two divergent documents.
// To do this, the server emebeds a random UUID in the document and

// Apollo's lib is commonjs and tsx doesn't see its exports, so work around it.
import * as apollo from "@apollo/client/core";
const { ApolloClient, createHttpLink, InMemoryCache } = apollo;

import { randomUUID } from "node:crypto";
import { Hocuspocus } from "@hocuspocus/server";
import { Logger } from "@hocuspocus/extension-logger";
import { setContext } from "@apollo/client/link/context";
import { env } from "node:process";
import * as Y from "yjs";

import { type ModelHandler } from "./base_handler";
import ObservationHandler from "./handlers/observation";

// Extend this with your model handlers. See how-to-collab.md.
const HANDLERS: Map<string, ModelHandler> = new Map([
    ["observation", ObservationHandler],
]);

// Graphql Client

const httpLink = createHttpLink({
    uri: "http://graphql_engine:8080/v1/graphql",
});

const authLink = setContext((_, { headers }) => {
    return {
        headers: {
            ...headers,
            "x-hasura-admin-secret": (env as any)[
                "HASURA_GRAPHQL_ADMIN_SECRET"
            ],
        },
    };
});

const gqlClient = new ApolloClient({
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

// Hocuspocus collab server

type Context = {
    model: string;
    id: number;
    username: string;
};

class AuthError extends Error {
    constructor(msg: string) {
        super(msg);
        this.name = "AuthError";
    }
}

const server = new Hocuspocus({
    port: 8000,
    extensions: [
        new Logger({
            onUpgrade: false,
        }),
    ],

    async onAuthenticate(conn) {
        try {
            const roomSplit = conn.documentName.split("/", 2);
            if (roomSplit.length !== 2) {
                throw new AuthError("Client Error: Invalid room name");
            }
            const model = roomSplit[0];
            const id = parseInt(roomSplit[1]);
            if (id !== id) {
                throw new AuthError(
                    "Client Error: Invalid room name: Invalid ID"
                );
            }

            if (!HANDLERS.has(model)) {
                throw new AuthError(
                    "Client error: unrecognized model: " + model
                );
            }

            const tokenParts = conn.token.split(" ");
            if (tokenParts.length !== 1 && tokenParts.length !== 2) {
                throw new AuthError("Client error: invalid auth token");
            }
            const token = tokenParts[0];
            const expectedInstanceId =
                tokenParts.length >= 2 ? tokenParts[1] : null;

            const res = await fetch(
                "http://django:8000/api/check_permissions",
                {
                    method: "POST",
                    body: JSON.stringify({
                        input: {
                            model,
                            id,
                        },
                    }),
                    headers: {
                        "Hasura-Action-Secret": (env as any)[
                            "HASURA_ACTION_SECRET"
                        ],
                        Authorization: "Bearer " + token,
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                }
            );

            if (res.status !== 200) {
                const body = await res.text();
                throw new AuthError("Auth failed: " + body);
            }

            const username = await res.json();
            if (typeof username !== "string") {
                throw new AuthError("Auth failed: " + JSON.stringify(username));
            }

            if (expectedInstanceId !== null) {
                // If a client was working with a previous version of the document, make sure the one
                // on the server matches, otherwise it'll try to merge two divergent yjs docs, which
                // causes weird results. Kick them out and make them reload if that happens.
                const existingDoc = conn.instance.documents.get(
                    conn.documentName
                );
                if (!existingDoc) {
                    throw new AuthError(
                        "Auth failed: client expecting a loaded document"
                    );
                }

                let instanceId;
                existingDoc.transact(() => {
                    instanceId = existingDoc
                        .get("serverInfo", Y.Map)
                        .get("instanceId");
                });

                if (expectedInstanceId !== instanceId) {
                    throw new AuthError(
                        "Auth failed: expected document instance ID mismatch"
                    );
                }
            }

            return {
                model,
                id,
                username,
            } as Context; // data.context
        } catch (e) {
            if (!(e instanceof AuthError)) console.error(e);
            throw e;
        }
    },

    async onLoadDocument(data) {
        try {
            const context = data.context as Context;
            const handler = HANDLERS.get(context.model)!;
            const doc = await handler.load(gqlClient, context.id);
            doc.transact(() => {
                // Embed an ID unique to this particular yjs doc, so a client working with an older version
                // won't try to merge with a divergent document and get weird results.
                doc.get("serverInfo", Y.Map).set("instanceId", randomUUID());
            });
            return doc;
        } catch (e) {
            console.error("onLoadDocument failed ", e);
            throw e;
        }
    },

    async onStoreDocument(data) {
        const context = data.context as Context;
        const handler = HANDLERS.get(context.model)!;
        await handler.save(gqlClient, context.id, data.document);
    },
});

server.listen();
