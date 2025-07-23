import * as Y from "yjs";
import { ApolloClient, TypedDocumentNode } from "@apollo/client";

/** Functions for loading, saving, and converting a type from/to YJS. */
export type ModelHandler = {
    load: (client: ApolloClient<unknown>, id: number) => Promise<Y.Doc>;
    save: (
        client: ApolloClient<unknown>,
        id: number,
        doc: Y.Doc
    ) => Promise<void>;
};

export type IdVars = { id: number };

/**
 * Make a `ModelHandler` from a simple GraphQL query.
 * @param getQuery The GraphQL query to load the model. Parameters must be `($id: bigint!)`.
 * @param setQuery The GraphQL query to save the model.
 * @param fillFields Function to set fields on a `Y.Doc` based on the results returned from the `getQuery`. Called in a YJS transaction.
 * @param mkQueryVars Function to get the parameters for the `setQuery` to save the model. Called in a YJS transaction.
 * @returns The model handler.
 */
export function simpleModelHandler<GetRes, SetRes, SetQueryVars>(
    getQuery: TypedDocumentNode<GetRes, IdVars>,
    setQuery: TypedDocumentNode<SetRes, SetQueryVars>,
    fillFields: (doc: Y.Doc, res: GetRes) => void,
    mkQueryVars: (doc: Y.Doc, id: number) => SetQueryVars
): ModelHandler {
    return {
        load: async (client, id) => {
            const res = await client.query({
                query: getQuery,
                variables: {
                    id,
                },
            });
            if (res.error || res.errors) {
                throw res.error || res.errors;
            }
            const doc = new Y.Doc();
            doc.transact(() => {
                fillFields(doc, res.data);
            });
            return doc;
        },
        async save(client, id, doc) {
            let queryVars;
            doc.transact(() => {
                queryVars = mkQueryVars(doc, id);
            });
            const res = await client.mutate({
                mutation: setQuery,
                variables: queryVars,
            });
            if (res.errors) {
                throw res.errors;
            }
        },
    };
}
