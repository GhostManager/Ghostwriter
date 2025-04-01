// Collaborative editing server, based on Hocuspocus
//
// Dynamically converts the standard models from the GraphQL API to/from YJS.

// Apollo's lib is commonjs and tsx doesn't see its exports, so work around it.
import * as apollo from "@apollo/client/core";
const { ApolloClient, createHttpLink, InMemoryCache } = apollo;

import { randomUUID } from "node:crypto";
import { Hocuspocus } from "@hocuspocus/server";
import { setContext } from "@apollo/client/link/context";
import { env } from "node:process";
import * as Y from "yjs";
import pino from "pino";
import { type Logger } from "pino";

import { type ModelHandler } from "./base_handler";
import ObservationHandler from "./handlers/observation";
import ReportObservationLinkHandler from "./handlers/report_observation_link";
import FindingHandler from "./handlers/finding";
import ReportFindingLinkHandler from "./handlers/report_finding_link";
import ReportHandler from "./handlers/report";

// Extend this with your model handlers. See how-to-collab.md.
const HANDLERS: Map<string, ModelHandler> = new Map([
    ["observation", ObservationHandler],
    ["report_observation_link", ReportObservationLinkHandler],
    ["finding", FindingHandler],
    ["report_finding_link", ReportFindingLinkHandler],
    ["report", ReportHandler],
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
    log: Logger;
};

class AuthError extends Error {
    constructor(msg: string) {
        super(msg);
        this.name = "AuthError";
    }
}

const BASE_LOGGER = pino({});

const server = new Hocuspocus({
    port: 8000,

    async onConnect(data) {
        BASE_LOGGER.info({
            docName: data.documentName,
            addr: data.request.socket.remoteAddress,
            port: data.request.socket.remotePort,
            socketId: data.socketId,
            msg: "Connected",
        });
    },

    async onAuthenticate(conn) {
        const log = BASE_LOGGER.child({
            docName: conn.documentName,
            addr: conn.request.socket.remoteAddress,
            port: conn.request.socket.remotePort,
            socketId: conn.socketId,
        });
        try {
            const roomSplit = conn.documentName.split("/", 2);
            if (roomSplit.length !== 2) {
                throw new AuthError("Invalid room name");
            }
            const model = roomSplit[0];
            const id = parseInt(roomSplit[1]);
            if (id !== id) {
                throw new AuthError("Invalid room name: Invalid ID");
            }

            if (!HANDLERS.has(model)) {
                throw new AuthError("Unrecognized model: " + model);
            }

            const tokenParts = conn.token.split(" ");
            if (tokenParts.length !== 1 && tokenParts.length !== 2) {
                throw new AuthError("Invalid auth token");
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
                if (res.status === 403)
                    throw new AuthError("User failed authentication: " + body);
                throw new Error("Auth endpoint failed:" + body);
            }

            const username = await res.json();
            if (typeof username !== "string") {
                throw new Error(
                    "Invalid data from auth endpoint " +
                        JSON.stringify(username)
                );
            }
            log.setBindings({ username });

            if (expectedInstanceId !== null) {
                // If a client was working with a previous version of the document, make sure the one
                // on the server matches, otherwise it'll try to merge two divergent yjs docs, which
                // causes weird results. Kick them out and make them reload if that happens.
                const existingDoc = conn.instance.documents.get(
                    conn.documentName
                );
                if (!existingDoc) {
                    throw new AuthError("client expecting a loaded document");
                }

                let instanceId;
                existingDoc.transact(() => {
                    instanceId = existingDoc
                        .get("serverInfo", Y.Map)
                        .get("instanceId");
                });

                if (expectedInstanceId !== instanceId) {
                    throw new AuthError(
                        "expected document instance ID mismatch"
                    );
                }
            }

            log.info("Client authenticated");
            return {
                model,
                id,
                username,
                log,
            } as Context; // data.context
        } catch (e) {
            if (e instanceof AuthError) {
                log.error({
                    msg: "Could not authenticate client: " + e.message,
                });
            } else {
                log.error({ msg: "Error authenticating", err: e });
            }
            throw e;
        }
    },

    async onLoadDocument(data) {
        const context = data.context as Context;
        try {
            context.log.info("Loading document");

            const handler = HANDLERS.get(context.model)!;
            const doc = await handler.load(gqlClient, context.id);
            doc.transact((tx) => {
                const serverInfo = tx.doc.get("serverInfo", Y.Map);
                // Embed an ID unique to this particular yjs doc, so a client working with an older version
                // won't try to merge with a divergent document and get weird results.
                serverInfo.set("instanceId", randomUUID());
                // Save error flag
                serverInfo.set("saveError", false);
            });
            return doc;
        } catch (e) {
            context.log.error({ msg: "Could not load document", err: e });
            throw e;
        }
    },

    async onStoreDocument(data) {
        const context = data.context as Context;
        try {
            context.log.info("Saving document");
            const handler = HANDLERS.get(context.model)!;
            await handler.save(gqlClient, context.id, data.document);
        } catch (e) {
            context.log.error({ msg: "Could not save document", err: e });
            data.document.transact((tx) => {
                tx.doc.get("serverInfo", Y.Map).set("saveError", true);
            });
            return;
        }
        data.document.transact((tx) => {
            tx.doc.get("serverInfo", Y.Map).set("saveError", false);
        });
    },

    async onDisconnect(data) {
        (data.context as Context).log.info("Disconnected");
    },
});

server.listen();
