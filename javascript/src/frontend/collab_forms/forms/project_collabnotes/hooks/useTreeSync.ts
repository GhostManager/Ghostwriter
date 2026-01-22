import { useEffect, useRef, useCallback } from "react";
import {
    HocuspocusProvider,
    HocuspocusProviderWebsocket,
} from "@hocuspocus/provider";

interface UseTreeSyncOptions {
    projectId: number;
    onTreeChanged: () => void;
}

/**
 * Hook for real-time tree synchronization across clients.
 *
 * Uses Hocuspocus stateless messages to broadcast "tree-changed" notifications.
 * When any client modifies the tree structure (create/delete/rename/move),
 * it calls notifyTreeChanged() which broadcasts to all other connected clients,
 * triggering their onTreeChanged callback to refetch the tree.
 */
export function useTreeSync({ projectId, onTreeChanged }: UseTreeSyncOptions) {
    const providerRef = useRef<HocuspocusProvider | null>(null);
    // Use a ref for the callback to avoid reconnecting when callback changes
    const onTreeChangedRef = useRef(onTreeChanged);
    onTreeChangedRef.current = onTreeChanged;

    useEffect(() => {
        const url = document.getElementById("yjs-url")?.innerHTML;
        const jwt = document.getElementById("yjs-jwt")?.innerHTML;

        if (!url || !jwt) {
            console.warn("useTreeSync: Missing yjs-url or yjs-jwt elements");
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
            onStateless: ({ payload }) => {
                try {
                    const msg = JSON.parse(payload);
                    if (msg.type === "tree-changed") {
                        onTreeChangedRef.current();
                    }
                } catch (e) {
                    console.error("useTreeSync: Failed to parse stateless message", e);
                }
            },
        });

        providerRef.current = provider;

        // Explicitly attach and connect
        provider.attach();
        websocketProvider.connect();

        return () => {
            provider.destroy();
            providerRef.current = null;
        };
    }, [projectId]);

    const notifyTreeChanged = useCallback(() => {
        if (providerRef.current) {
            providerRef.current.sendStateless(
                JSON.stringify({ type: "tree-changed", timestamp: Date.now() })
            );
        }
    }, []);

    return { notifyTreeChanged };
}
