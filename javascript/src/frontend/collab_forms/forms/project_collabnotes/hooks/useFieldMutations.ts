import { useCallback } from "react";

const CREATE_RICH_TEXT_FIELD_MUTATION = `
    mutation CreateRichTextField($noteId: bigint!, $position: Int!) {
        insert_projectCollabNoteField_one(object: {
            noteId: $noteId,
            fieldType: "rich_text",
            content: "",
            position: $position
        }) {
            id
            position
        }
    }
`;

const DELETE_FIELD_MUTATION = `
    mutation DeleteProjectCollabNoteField($id: bigint!) {
        delete_projectCollabNoteField_by_pk(id: $id) {
            id
        }
    }
`;

const UPDATE_FIELD_POSITION_MUTATION = `
    mutation UpdateFieldPosition($id: bigint!, $position: Int!) {
        update_projectCollabNoteField_by_pk(
            pk_columns: { id: $id },
            _set: { position: $position }
        ) {
            id
        }
    }
`;

const REORDER_FIELDS_MUTATION = `
    mutation ReorderFields($updates: [projectCollabNoteField_insert_input!]!) {
        insert_projectCollabNoteField(
            objects: $updates,
            on_conflict: {
                constraint: projectcollabnotefield_pkey,
                update_columns: [position]
            }
        ) {
            affected_rows
        }
    }
`;

const GET_MAX_POSITION = `
    query GetMaxFieldPosition($noteId: bigint!) {
        projectCollabNoteField_aggregate(
            where: { noteId: { _eq: $noteId } }
        ) {
            aggregate {
                max {
                    position
                }
            }
        }
    }
`;

function getJwt(): string {
    return document.getElementById("yjs-jwt")?.innerHTML ?? "";
}

async function graphqlMutate(query: string, variables: Record<string, unknown>) {
    const response = await fetch("/v1/graphql", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${getJwt()}`,
        },
        body: JSON.stringify({ query, variables }),
    });
    const data = await response.json();
    if (data.errors) {
        throw new Error(data.errors[0]?.message || "GraphQL error");
    }
    return data.data;
}

export function useFieldMutations() {
    const getNextPosition = useCallback(
        async (noteId: number): Promise<number> => {
            const data = await graphqlMutate(GET_MAX_POSITION, { noteId });
            const maxPos =
                data.projectCollabNoteField_aggregate.aggregate.max.position;
            return maxPos !== null ? maxPos + 1 : 0;
        },
        []
    );

    const createRichTextField = useCallback(
        async (noteId: number): Promise<{ id: string; position: number }> => {
            const position = await getNextPosition(noteId);
            const data = await graphqlMutate(CREATE_RICH_TEXT_FIELD_MUTATION, {
                noteId,
                position,
            });
            return {
                id: data.insert_projectCollabNoteField_one.id.toString(),
                position: data.insert_projectCollabNoteField_one.position,
            };
        },
        [getNextPosition]
    );

    const deleteField = useCallback(async (id: string): Promise<void> => {
        await graphqlMutate(DELETE_FIELD_MUTATION, { id: parseInt(id) });
    }, []);

    const updateFieldPosition = useCallback(
        async (id: string, position: number): Promise<void> => {
            await graphqlMutate(UPDATE_FIELD_POSITION_MUTATION, {
                id: parseInt(id),
                position,
            });
        },
        []
    );

    const reorderFields = useCallback(
        async (
            fields: Array<{ id: string; position: number; noteId: number }>
        ): Promise<void> => {
            const updates = fields.map((field) => ({
                id: parseInt(field.id),
                noteId: field.noteId,
                position: field.position,
            }));
            await graphqlMutate(REORDER_FIELDS_MUTATION, { updates });
        },
        []
    );

    return {
        createRichTextField,
        deleteField,
        updateFieldPosition,
        reorderFields,
    };
}
