import { type ApolloClient } from "@apollo/client";
import { expect, test } from "@playwright/test";
import * as Y from "yjs";

import ReportFindingLinkHandler from "../../src/collab_server/handlers/report_finding_link";

type ReportFindingLinkData = {
    extraFieldSpec: { internalName: string; type: string }[];
    savedSeverityId: number | null;
};

type SaveVariables = {
    set: Record<string, unknown>;
};

function createDocument(severityId: number): Y.Doc {
    const doc = new Y.Doc();
    doc.get("plain_fields", Y.Map).set("severityId", severityId);
    return doc;
}

function createData(savedSeverityId: number): ReportFindingLinkData {
    return {
        extraFieldSpec: [],
        savedSeverityId,
    };
}

function createClient(
    mutate: (variables: SaveVariables) => Promise<unknown>
): ApolloClient<unknown> {
    return {
        mutate: ({ variables }: { variables: SaveVariables }) =>
            mutate(variables),
    } as unknown as ApolloClient<unknown>;
}

test.describe("report finding collaboration saves", () => {
    test("omits an unchanged severity from unrelated saves", async () => {
        const doc = createDocument(1);
        const data = createData(1);
        let databaseSeverityId = 2;
        let savedVariables: SaveVariables | undefined;
        const client = createClient(async (variables) => {
            savedVariables = variables;
            if (
                Object.prototype.hasOwnProperty.call(
                    variables.set,
                    "severityId"
                )
            ) {
                databaseSeverityId = variables.set.severityId as number;
            }
            return {};
        });

        await ReportFindingLinkHandler.save(client, 7, doc, data);

        expect(savedVariables).toBeDefined();
        expect(savedVariables!.set).not.toHaveProperty("severityId");
        expect(databaseSeverityId).toBe(2);
        expect(data.savedSeverityId).toBe(1);
    });

    test("records a changed severity only after a successful save", async () => {
        const doc = createDocument(2);
        const data = createData(1);
        const saves: SaveVariables[] = [];
        const client = createClient(async (variables) => {
            saves.push(variables);
            return {};
        });

        await ReportFindingLinkHandler.save(client, 7, doc, data);
        await ReportFindingLinkHandler.save(client, 7, doc, data);

        expect(saves[0].set).toHaveProperty("severityId", 2);
        expect(saves[1].set).not.toHaveProperty("severityId");
        expect(data.savedSeverityId).toBe(2);
    });

    test("keeps a failed severity change dirty for retry", async () => {
        const doc = createDocument(2);
        const data = createData(1);
        const failure = new Error("save failed");
        const failingClient = createClient(async () => ({
            errors: [failure],
        }));

        await expect(
            ReportFindingLinkHandler.save(failingClient, 7, doc, data)
        ).rejects.toEqual([failure]);
        expect(data.savedSeverityId).toBe(1);

        let retryVariables: SaveVariables | undefined;
        const successfulClient = createClient(async (variables) => {
            retryVariables = variables;
            return {};
        });
        await ReportFindingLinkHandler.save(successfulClient, 7, doc, data);

        expect(retryVariables).toBeDefined();
        expect(retryVariables!.set).toHaveProperty("severityId", 2);
        expect(data.savedSeverityId).toBe(2);
    });

    test("keeps a newer in-flight severity change dirty", async () => {
        const doc = createDocument(2);
        const data = createData(1);
        let firstVariables: SaveVariables | undefined;
        let resolveFirstSave: ((value: unknown) => void) | undefined;
        const firstClient = createClient(
            (variables) =>
                new Promise((resolve) => {
                    firstVariables = variables;
                    resolveFirstSave = resolve;
                })
        );

        const firstSave = ReportFindingLinkHandler.save(
            firstClient,
            7,
            doc,
            data
        );
        expect(firstVariables).toBeDefined();
        expect(firstVariables!.set).toHaveProperty("severityId", 2);

        doc.get("plain_fields", Y.Map).set("severityId", 3);
        resolveFirstSave!({});
        await firstSave;

        expect(data.savedSeverityId).toBe(2);

        let secondVariables: SaveVariables | undefined;
        const secondClient = createClient(async (variables) => {
            secondVariables = variables;
            return {};
        });
        await ReportFindingLinkHandler.save(secondClient, 7, doc, data);

        expect(secondVariables).toBeDefined();
        expect(secondVariables!.set).toHaveProperty("severityId", 3);
        expect(data.savedSeverityId).toBe(3);
    });
});
