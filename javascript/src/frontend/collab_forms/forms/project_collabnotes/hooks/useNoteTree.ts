import { useState, useEffect, useCallback } from "react";
import { NoteTreeNode, FlatNote } from "../types";

const QUERY = `
    query GetNoteTree($projectId: bigint!) {
        projectCollabNote(
            where: { projectId: { _eq: $projectId } },
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

function getJwt(): string {
    return document.getElementById("yjs-jwt")?.innerHTML ?? "";
}

export function useNoteTree(projectId: number) {
    const [flatNodes, setFlatNodes] = useState<FlatNote[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchTree = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch("/v1/graphql", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${getJwt()}`,
                },
                body: JSON.stringify({
                    query: QUERY,
                    variables: { projectId },
                }),
            });
            const data = await response.json();
            if (data.errors) {
                throw new Error(data.errors[0]?.message || "GraphQL error");
            }
            setFlatNodes(data.data.projectCollabNote || []);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to fetch notes");
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        fetchTree();
    }, [fetchTree]);

    // Build tree structure from flat nodes
    const tree = buildTree(flatNodes);

    return { tree, flatNodes, loading, error, refetch: fetchTree };
}

function buildTree(flatNodes: FlatNote[]): NoteTreeNode[] {
    const nodeMap = new Map<number, NoteTreeNode>();
    const roots: NoteTreeNode[] = [];

    // First pass: create all nodes
    for (const node of flatNodes) {
        nodeMap.set(node.id, {
            ...node,
            children: [],
        });
    }

    // Second pass: build parent-child relationships
    for (const node of flatNodes) {
        const treeNode = nodeMap.get(node.id)!;
        if (node.parentId === null) {
            roots.push(treeNode);
        } else {
            const parent = nodeMap.get(node.parentId);
            if (parent) {
                parent.children.push(treeNode);
            } else {
                // Parent doesn't exist (orphan), add to root
                roots.push(treeNode);
            }
        }
    }

    return roots;
}
