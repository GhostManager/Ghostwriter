import { useEffect, useRef, useCallback, useState } from "react";
import {
    HocuspocusProvider,
    HocuspocusProviderWebsocket,
} from "@hocuspocus/provider";
import * as Y from "yjs";
import type { FlatNote, NoteTreeNode } from "../types";

interface UseTreeSyncOptions {
    projectId: number;
}

/**
 * Hook for real-time tree synchronization across clients using Yjs.
 *
 * Instead of broadcasting "tree-changed" messages and re-fetching from GraphQL,
 * the tree structure is stored in a Yjs shared Y.Array. When any client modifies
 * the tree (create/delete/rename/move), it updates both the database (via GraphQL)
 * and the Yjs array. Other clients see changes via Yjs sync automatically.
 */
export function useTreeSync({ projectId }: UseTreeSyncOptions) {
    const providerRef = useRef<HocuspocusProvider | null>(null);
    const [flatNodes, setFlatNodes] = useState<FlatNote[]>([]);
    const [loading, setLoading] = useState(true);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const url = document.getElementById("yjs-url")?.innerHTML;
        const jwt = document.getElementById("yjs-jwt")?.innerHTML;

        if (!url || !jwt) {
            console.warn("useTreeSync: Missing yjs-url or yjs-jwt elements");
            setLoading(false);
            return;
        }

        const websocketProvider = new HocuspocusProviderWebsocket({
            url,
            autoConnect: false,
        });

        const provider = new HocuspocusProvider({
            websocketProvider,
            name: `project_tree_sync/${projectId}`,
            token: jwt,
            onSynced() {
                setConnected(true);
                setLoading(false);
                // Read initial tree from Yjs doc
                const treeArray = provider.document.get("tree", Y.Array) as Y.Array<FlatNote>;
                const nodes: FlatNote[] = [];
                for (let i = 0; i < treeArray.length; i++) {
                    nodes.push(treeArray.get(i));
                }
                setFlatNodes(nodes);
            },
        });

        providerRef.current = provider;

        // Observe changes to the tree array
        const treeArray = provider.document.get("tree", Y.Array) as Y.Array<FlatNote>;
        const observer = () => {
            const nodes: FlatNote[] = [];
            for (let i = 0; i < treeArray.length; i++) {
                nodes.push(treeArray.get(i));
            }
            setFlatNodes(nodes);
        };
        treeArray.observeDeep(observer);

        provider.attach();
        websocketProvider.connect();

        return () => {
            treeArray.unobserveDeep(observer);
            provider.destroy();
            providerRef.current = null;
        };
    }, [projectId]);

    /** Replace the entire tree array in the Yjs doc with new nodes. */
    const updateTree = useCallback(
        (newNodes: FlatNote[]) => {
            const provider = providerRef.current;
            if (!provider) return;
            const treeArray = provider.document.get("tree", Y.Array) as Y.Array<FlatNote>;
            provider.document.transact(() => {
                treeArray.delete(0, treeArray.length);
                if (newNodes.length > 0) {
                    treeArray.push(newNodes);
                }
            });
        },
        []
    );

    /** Add a single node to the tree array. */
    const addNode = useCallback(
        (node: FlatNote) => {
            const provider = providerRef.current;
            if (!provider) return;
            const treeArray = provider.document.get("tree", Y.Array) as Y.Array<FlatNote>;
            treeArray.push([node]);
        },
        []
    );

    /** Remove a node (and optionally its descendants) from the tree array. */
    const removeNodes = useCallback(
        (ids: Set<number>) => {
            const provider = providerRef.current;
            if (!provider) return;
            const treeArray = provider.document.get("tree", Y.Array) as Y.Array<FlatNote>;
            provider.document.transact(() => {
                // Iterate backwards to safely delete by index
                for (let i = treeArray.length - 1; i >= 0; i--) {
                    const node = treeArray.get(i);
                    if (ids.has(node.id)) {
                        treeArray.delete(i, 1);
                    }
                }
            });
        },
        []
    );

    /** Update a node's properties in the tree array. */
    const updateNode = useCallback(
        (id: number, updates: Partial<FlatNote>) => {
            const provider = providerRef.current;
            if (!provider) return;
            const treeArray = provider.document.get("tree", Y.Array) as Y.Array<FlatNote>;
            provider.document.transact(() => {
                for (let i = 0; i < treeArray.length; i++) {
                    const node = treeArray.get(i);
                    if (node.id === id) {
                        treeArray.delete(i, 1);
                        treeArray.insert(i, [{ ...node, ...updates }]);
                        break;
                    }
                }
            });
        },
        []
    );

    // Build tree structure from flat nodes
    const tree = buildTree(flatNodes);

    return {
        tree,
        flatNodes,
        loading,
        connected,
        updateTree,
        addNode,
        removeNodes,
        updateNode,
    };
}

function buildTree(flatNodes: FlatNote[]): NoteTreeNode[] {
    const nodeMap = new Map<number, NoteTreeNode>();
    const roots: NoteTreeNode[] = [];

    for (const node of flatNodes) {
        nodeMap.set(node.id, { ...node, children: [] });
    }

    for (const node of flatNodes) {
        const treeNode = nodeMap.get(node.id)!;
        if (node.parentId === null) {
            roots.push(treeNode);
        } else {
            const parent = nodeMap.get(node.parentId);
            if (parent) {
                parent.children.push(treeNode);
            } else {
                roots.push(treeNode);
            }
        }
    }

    return roots;
}
