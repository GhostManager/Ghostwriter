import { type ModelHandler } from "../base_handler";
import * as Y from "yjs";
import { ApolloClient, gql as rawGql } from "@apollo/client/core";

const GET_TREE_QUERY = rawGql`
    query GET_PROJECT_TREE($id: bigint!) {
        projectCollabNote(
            where: { projectId: { _eq: $id } }
            order_by: [{ position: asc }, { title: asc }]
        ) {
            id
            title
            nodeType
            parentId
            position
        }
    }
`;

interface TreeNode {
    id: number;
    title: string;
    nodeType: string;
    parentId: number | null;
    position: number;
}

const ProjectTreeSyncHandler: ModelHandler<null> = {
    async load(client: ApolloClient<unknown>, id: number) {
        const res = await client.query({
            query: GET_TREE_QUERY,
            variables: { id },
        });
        if (res.error || res.errors) throw res.error || res.errors;

        const doc = new Y.Doc();
        doc.transact(() => {
            const treeArray = doc.get("tree", Y.Array) as Y.Array<TreeNode>;
            const nodes: TreeNode[] = res.data.projectCollabNote || [];
            if (nodes.length > 0) {
                treeArray.push(nodes);
            }
        });

        return [doc, null];
    },

    async save() {
        // Tree data is persisted via GraphQL mutations from the frontend.
        // The Yjs doc here acts as a real-time sync cache only.
    },
};

export default ProjectTreeSyncHandler;
