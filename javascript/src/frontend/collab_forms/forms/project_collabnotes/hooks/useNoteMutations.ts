import { useCallback } from "react";

const CREATE_ROOT_MUTATION = `
    mutation CreateRootProjectCollabNote(
        $projectId: bigint!,
        $title: String!,
        $nodeType: String!,
        $position: Int!
    ) {
        insert_projectCollabNote_one(object: {
            projectId: $projectId,
            title: $title,
            nodeType: $nodeType,
            content: "",
            position: $position
        }) {
            id
        }
    }
`;

const CREATE_CHILD_MUTATION = `
    mutation CreateChildProjectCollabNote(
        $projectId: bigint!,
        $parentId: bigint!,
        $title: String!,
        $nodeType: String!,
        $position: Int!
    ) {
        insert_projectCollabNote_one(object: {
            projectId: $projectId,
            parentId: $parentId,
            title: $title,
            nodeType: $nodeType,
            content: "",
            position: $position
        }) {
            id
        }
    }
`;

const UPDATE_TITLE_MUTATION = `
    mutation UpdateProjectCollabNoteTitle($id: bigint!, $title: String!) {
        update_projectCollabNote_by_pk(
            pk_columns: { id: $id },
            _set: { title: $title }
        ) {
            id
        }
    }
`;

const DELETE_MUTATION = `
    mutation DeleteProjectCollabNote($id: bigint!) {
        delete_projectCollabNote_by_pk(id: $id) {
            id
        }
    }
`;

const DELETE_NOTE_FIELDS_MUTATION = `
    mutation DeleteNoteFields($noteId: bigint!) {
        delete_projectCollabNoteField(where: { noteId: { _eq: $noteId } }) {
            affected_rows
        }
    }
`;

const MOVE_MUTATION = `
    mutation MoveProjectCollabNote($id: bigint!, $parentId: bigint, $position: Int!) {
        update_projectCollabNote_by_pk(
            pk_columns: { id: $id },
            _set: { parentId: $parentId, position: $position }
        ) {
            id
        }
    }
`;

const GET_MAX_POSITION_ROOT = `
    query GetMaxPositionRoot($projectId: bigint!) {
        projectCollabNote_aggregate(
            where: {
                projectId: { _eq: $projectId },
                parentId: { _is_null: true }
            }
        ) {
            aggregate {
                max {
                    position
                }
            }
        }
    }
`;

const GET_MAX_POSITION_CHILD = `
    query GetMaxPositionChild($projectId: bigint!, $parentId: bigint!) {
        projectCollabNote_aggregate(
            where: {
                projectId: { _eq: $projectId },
                parentId: { _eq: $parentId }
            }
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

export function useNoteMutations() {
    const getNextPosition = useCallback(
        async (projectId: number, parentId: number | null): Promise<number> => {
            const query = parentId === null ? GET_MAX_POSITION_ROOT : GET_MAX_POSITION_CHILD;
            const variables = parentId === null
                ? { projectId }
                : { projectId, parentId };
            const data = await graphqlMutate(query, variables);
            const maxPos =
                data.projectCollabNote_aggregate.aggregate.max.position;
            // Use 1000-gap to allow room for reordering between items
            return maxPos !== null ? maxPos + 1000 : 0;
        },
        []
    );

    const createNote = useCallback(
        async (
            projectId: number,
            parentId: number | null,
            title: string
        ): Promise<number> => {
            const position = await getNextPosition(projectId, parentId);
            const mutation = parentId === null ? CREATE_ROOT_MUTATION : CREATE_CHILD_MUTATION;
            const variables = parentId === null
                ? { projectId, title, nodeType: "note", position }
                : { projectId, parentId, title, nodeType: "note", position };
            const data = await graphqlMutate(mutation, variables);
            return data.insert_projectCollabNote_one.id;
        },
        [getNextPosition]
    );

    const createFolder = useCallback(
        async (
            projectId: number,
            parentId: number | null,
            title: string
        ): Promise<number> => {
            const position = await getNextPosition(projectId, parentId);
            const mutation = parentId === null ? CREATE_ROOT_MUTATION : CREATE_CHILD_MUTATION;
            const variables = parentId === null
                ? { projectId, title, nodeType: "folder", position }
                : { projectId, parentId, title, nodeType: "folder", position };
            const data = await graphqlMutate(mutation, variables);
            return data.insert_projectCollabNote_one.id;
        },
        [getNextPosition]
    );

    const renameNote = useCallback(
        async (id: number, title: string): Promise<void> => {
            await graphqlMutate(UPDATE_TITLE_MUTATION, { id, title });
        },
        []
    );

    const deleteNote = useCallback(async (id: number): Promise<void> => {
        // First delete all fields associated with this note (cascade delete)
        await graphqlMutate(DELETE_NOTE_FIELDS_MUTATION, { noteId: id });
        // Then delete the note itself
        await graphqlMutate(DELETE_MUTATION, { id });
    }, []);

    const moveNote = useCallback(
        async (
            id: number,
            parentId: number | null,
            position: number
        ): Promise<void> => {
            await graphqlMutate(MOVE_MUTATION, { id, parentId, position });
        },
        []
    );

    return {
        createNote,
        createFolder,
        renameNote,
        deleteNote,
        moveNote,
    };
}
