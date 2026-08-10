import assert from "node:assert/strict";
import { gql } from "@apollo/client/core";
import { createServer, type IncomingHttpHeaders } from "node:http";
import type { AddressInfo } from "node:net";

import { createCollabGqlClient } from "./graphql_client";

let requestHeaders: IncomingHttpHeaders | undefined;
const server = createServer((request, response) => {
    requestHeaders = request.headers;
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ data: { tags: { tags: [] } } }));
});

await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
const { port } = server.address() as AddressInfo;

try {
    const client = createCollabGqlClient(
        "scoped-collaboration-token",
        `http://127.0.0.1:${port}/v1/graphql`
    );
    await client.query({
        query: gql`
            query GetTags {
                tags(model: "report_finding_link", id: 1) {
                    tags
                }
            }
        `,
    });

    assert.equal(
        requestHeaders?.authorization,
        "Bearer scoped-collaboration-token"
    );
    console.log("Collaboration GraphQL authorization header check passed.");
} finally {
    await new Promise<void>((resolve, reject) =>
        server.close((error) => (error ? reject(error) : resolve()))
    );
}
