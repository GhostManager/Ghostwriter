// Collaborative editing server, based on Hocuspocus
//
// Dynamically converts the standard models from the GraphQL API to/from YJS.

// Apollo's lib is commonjs and tsx doesn't see its exports, so work around it.
import * as apollo from "@apollo/client/core";
import type {
    ApolloClient as ApolloClientType,
    NormalizedCacheObject,
} from "@apollo/client/core";
const { ApolloClient, createHttpLink, InMemoryCache } = apollo;

import { randomUUID } from "node:crypto";
import { Server } from "@hocuspocus/server";
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
import ProjectHandler from "./handlers/project";
import { setSaveError } from "./save_error";

// Extend this with your model handlers. See how-to-collab.md.
const HANDLERS_ARR: [string, ModelHandler<any>][] = [
    ["observation", ObservationHandler],
    ["report_observation_link", ReportObservationLinkHandler],
    ["finding", FindingHandler],
    ["report_finding_link", ReportFindingLinkHandler],
    ["report", ReportHandler],
    ["project", ProjectHandler],
];
const HANDLERS: Map<string, ModelHandler<any>> = new Map(HANDLERS_ARR);

// Graphql Client

const graphql_engine_hostname: string =
    env["HASURA_GRAPHQL_SERVER_HOSTNAME"] || "graphql_engine";

const httpLink = createHttpLink({
    uri: "http://" + graphql_engine_hostname + ":8080/v1/graphql",
});

function getGqlClient(context: Context) {
    if (context.gqlClient) return context.gqlClient;

    const authLink = setContext((_, { headers }) => {
        return {
            headers: {
                ...headers,
                "x-hasura-admin-secret": (env as any)[
                    "HASURA_GRAPHQL_ADMIN_SECRET"
                ],
                Authorization: "Bearer " + context.token,
            },
        };
    });

    context.gqlClient = new ApolloClient({
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
    return context.gqlClient;
}

// Hocuspocus collab server

/// Per-user context
type Context = {
    model: string;
    id: number;
    userId: number;
    username: string;
    token: string;
    expiresAt: number;
    log: Logger;
    gqlClient?: ApolloClientType<NormalizedCacheObject>;
};

class AuthError extends Error {
    constructor(msg: string) {
        super(msg);
        this.name = "AuthError";
    }
}

const BASE_LOGGER = pino({});
const documentData = new Map<string, unknown>();
const AUTH_TIMEOUT_MS = 15_000;

type AuthenticationData = {
    documentName: string;
    token: string;
    instance: {
        documents: ReadonlyMap<string, Y.Doc>;
    };
};

async function authenticateConnection(
    conn: AuthenticationData,
    log: Logger
): Promise<Context> {
    const roomMatch = /^([^/]+)\/([1-9]\d*)$/.exec(conn.documentName);
    if (roomMatch === null) {
        throw new AuthError("Invalid room name");
    }

    const model = roomMatch[1];
    const id = Number(roomMatch[2]);
    if (!Number.isSafeInteger(id) || !HANDLERS.has(model)) {
        throw new AuthError("Unrecognized document");
    }

    const tokenParts = conn.token.trim().split(/\s+/);
    if (tokenParts.length !== 1 && tokenParts.length !== 2) {
        throw new AuthError("Invalid auth token");
    }
    const [token, expectedInstanceId = null] = tokenParts;

    const res = await fetch("http://django:8000/api/check_permissions", {
        method: "POST",
        signal: AbortSignal.timeout(AUTH_TIMEOUT_MS),
        body: JSON.stringify({
            input: {
                model,
                id,
            },
        }),
        headers: {
            "Hasura-Action-Secret": (env as any)["HASURA_ACTION_SECRET"],
            Authorization: "Bearer " + token,
            "Content-Type": "application/json",
            Accept: "application/json",
        },
    });

    if (res.status !== 200) {
        const body = await res.text();
        if (res.status === 400 || res.status === 401 || res.status === 403) {
            throw new AuthError("User failed authentication: " + body);
        }
        throw new Error("Auth endpoint failed: " + body);
    }

    const principal = await res.json();
    if (
        typeof principal?.username !== "string" ||
        !Number.isSafeInteger(principal?.userId) ||
        !Number.isSafeInteger(principal?.expiresAt) ||
        principal.expiresAt * 1000 <= Date.now()
    ) {
        throw new Error(
            "Invalid data from auth endpoint " + JSON.stringify(principal)
        );
    }

    if (expectedInstanceId !== null) {
        // Refuse to merge a client document with a divergent server history.
        const existingDoc = conn.instance.documents.get(conn.documentName);
        if (!existingDoc) {
            throw new AuthError("client expecting a loaded document");
        }

        let instanceId;
        existingDoc.transact(() => {
            instanceId = existingDoc.get("serverInfo", Y.Map).get("instanceId");
        });

        if (expectedInstanceId !== instanceId) {
            throw new AuthError("expected document instance ID mismatch");
        }
    }

    return {
        model,
        id,
        userId: principal.userId,
        username: principal.username,
        token,
        expiresAt: principal.expiresAt,
        log,
    };
}

function requireValidToken(context: Context) {
    if (context.expiresAt * 1000 <= Date.now()) {
        throw new AuthError("Collaboration token expired");
    }
}

async function storeDocument(
    context: Context,
    documentName: string,
    document: Y.Doc
) {
    try {
        requireValidToken(context);
        const docData = documentData.get(documentName);
        context.log.info("Saving document");
        const handler = HANDLERS.get(context.model)!;
        await handler.save(
            getGqlClient(context),
            context.id,
            document,
            docData
        );
    } catch (e) {
        context.log.error({ msg: "Could not save document", err: e });
        setSaveError(document, true);
        return;
    }
    setSaveError(document, false);
}

const server = new Server({
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
            const context = await authenticateConnection(conn, log);
            log.setBindings({ username: context.username });
            log.info("Client authenticated");
            return context;
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

    async onTokenSync(data) {
        const currentContext = data.context as Context;
        try {
            const refreshedContext = await authenticateConnection(
                data,
                currentContext.log
            );
            if (refreshedContext.userId !== currentContext.userId) {
                throw new AuthError("Collaboration user changed");
            }

            // Mutate the existing object so any debounced save that already
            // captured this context also receives the renewed credential.
            Object.assign(data.connection.context, refreshedContext);
            currentContext.log.info("Collaboration token refreshed");

            await data.document.saveMutex.runExclusive(async () => {
                const serverInfo = data.document.get("serverInfo", Y.Map);
                if (serverInfo.get("saveError")) {
                    await storeDocument(
                        currentContext,
                        data.documentName,
                        data.document
                    );
                }
            });
        } catch (e) {
            currentContext.log.error({
                msg: "Could not refresh collaboration token",
                err: e,
            });
            throw e;
        }
    },

    async onLoadDocument(data) {
        const context = data.context as Context;
        try {
            requireValidToken(context);
            context.log.info("Loading document");

            const handler = HANDLERS.get(context.model)!;
            const [doc, docData] = await handler.load(
                getGqlClient(context),
                context.id
            );
            doc.transact((tx) => {
                const serverInfo = tx.doc.get("serverInfo", Y.Map);
                // Embed an ID unique to this particular yjs doc, so a client working with an older version
                // won't try to merge with a divergent document and get weird results.
                serverInfo.set("instanceId", randomUUID());
                // Save error flag
                serverInfo.set("saveError", false);
            });
            documentData.set(data.documentName, docData);
            return doc;
        } catch (e) {
            context.log.error({ msg: "Could not load document", err: e });
            throw e;
        }
    },

    async onStoreDocument(data) {
        const context = data.context as Context;
        await storeDocument(context, data.documentName, data.document);
    },

    async onDisconnect(data) {
        (data.context as Context).log.info("Disconnected");
    },

    async afterUnloadDocument(data) {
        documentData.delete(data.documentName);
    },
});

server.listen();
