import * as Y from "yjs";
import {
    ApolloClient,
    OperationVariables,
    TypedDocumentNode,
} from "@apollo/client";

/** Functions for loading, saving, and converting a type from/to YJS. */
export type ModelHandler<T, P = unknown> = {
    load: (client: ApolloClient<unknown>, id: number) => Promise<[Y.Doc, T]>;
    getSavePayload: (id: number, doc: Y.Doc, data: T) => P;
    save: (client: ApolloClient<unknown>, payload: P, data: T) => Promise<void>;
    markSaved?: (payload: P, data: T) => void;
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
export function simpleModelHandler<
    GetRes,
    SetRes,
    SetQueryVars extends OperationVariables,
    T,
>(
    getQuery: TypedDocumentNode<GetRes, IdVars>,
    setQuery: TypedDocumentNode<SetRes, SetQueryVars>,
    fillFields: (doc: Y.Doc, res: GetRes) => T,
    mkQueryVars: (doc: Y.Doc, id: number, data: T) => SetQueryVars
): ModelHandler<T, SetQueryVars> {
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
            let data: T;
            doc.transact(() => {
                data = fillFields(doc, res.data);
            });
            return [doc, data!];
        },
        getSavePayload(id, doc, data) {
            let queryVars: SetQueryVars | undefined;
            doc.transact(() => {
                queryVars = mkQueryVars(doc, id, data);
            });
            return queryVars!;
        },
        async save(client, payload) {
            const res = await client.mutate({
                mutation: setQuery,
                variables: payload,
            });
            if (res.errors) {
                throw res.errors;
            }
        },
    };
}
