import { useEffect, useRef, useState } from "react";
import { HocuspocusProvider } from "@hocuspocus/provider";
import * as Y from "yjs";

export type ConnectionStatus =
    | "disconnected"
    | "connecting"
    | "initialSyncing"
    | "syncing"
    | "error"
    | "idle";

/// Gets a YJS connection from the information embedded by the `collab_editing/update.html` view.
export function usePageConnection(settings: {
    model: string;
    yjs_url?: string;
    id?: string;
}): {
    // The YJS provider
    provider: HocuspocusProvider;
    // Detailed connection status
    status: ConnectionStatus;
    // A simple yes-no for whether or not controls should be enabled. Derived from `status` but provided here for convenience.
    connected: boolean;
} {
    const [status, setStatus] = useState<
        "disconnected" | "connecting" | "connected"
    >("disconnected");
    const [synced, setSynced] = useState<boolean>(false);
    const [initialSyncDone, setInitialSyncDone] = useState<boolean>(false);
    const savedInstanceID = useRef<string | null>(null);

    // Type as `HocuspocusProvider` only, cuz it's only going to be null for a slight bit.
    const provider = useRef<HocuspocusProvider>(
        null as unknown as HocuspocusProvider
    );

    // Not doing this inside of useEffect because we need to return the provider from this function - useEffect
    // is delayed.
    if (provider.current === null) {
        const url =
            settings.yjs_url ?? document.getElementById("yjs-url")!.innerHTML;
        const id =
            settings.id ?? document.getElementById("yjs-object-id")!.innerHTML;
        const username = document.getElementById("yjs-username")!.innerHTML;
        const jwt = document.getElementById("yjs-jwt")!.innerHTML;

        provider.current = new HocuspocusProvider({
            connect: false,
            url,
            name: settings.model + "/" + id,
            token() {
                let tok = jwt;

                // Send document instance ID so that server will kick us out if it's made a new document with
                // a divergent history.
                if (savedInstanceID.current !== null)
                    tok += " " + savedInstanceID.current;
                return tok;
            },
            onStatus(event) {
                setStatus(event.status);
                if (event.status !== "connected") setInitialSyncDone(false);
            },
            onSynced(event) {
                const state = event.state;
                setSynced(state);
                if (state) setInitialSyncDone(true);

                if (savedInstanceID.current === null) {
                    const doc = provider.current.document;
                    doc.transact(() => {
                        savedInstanceID.current = doc
                            .get("serverInfo", Y.Map)
                            .get("instanceId") as string;
                    });
                }
            },
        });

        provider.current.awareness!.setLocalStateField("user", {
            name: username,
            color: hsv_to_rgb(
                (provider.current.document.clientID % 255) / 255.0,
                0.5,
                1.0
            ),
        });

        // Export connection for debugging
        (window as any).gwDebugYjsProvider = provider.current;
    }

    useEffect(() => {
        provider.current!.connect();
        return () => {
            provider.current?.destroy();
            (window as any).gwDebugYjsProvider = null;
        };
    }, []);

    const [hasSaveError, setHasSaveError] = useState(false);
    useEffect(() => {
        const serverInfo = provider.current!.document.get("serverInfo", Y.Map);
        const cb = () => {
            setHasSaveError(!!serverInfo.get("saveError"));
        };
        serverInfo.observe(cb);
        return () => {
            serverInfo.unobserve(cb);
        };
    });

    let outStatus: ConnectionStatus;
    if (status === "connected") {
        if (!initialSyncDone) outStatus = "initialSyncing";
        else if (!synced) outStatus = "syncing";
        else if (hasSaveError) outStatus = "error";
        else outStatus = "idle";
    } else {
        outStatus = status;
    }

    return {
        provider: provider.current,
        status: outStatus,
        connected:
            outStatus === "idle" ||
            outStatus === "syncing" ||
            outStatus === "error",
    };
}

function hsv_to_rgb(h: number, s: number, v: number) {
    const i = Math.floor(h * 6);
    const f = h * 6 - i;
    const p = v * (1 - s);
    const q = v * (1 - f * s);
    const t = v * (1 - (1 - f) * s);

    let r, g, b;
    switch (i % 6) {
        case 0:
            (r = v), (g = t), (b = p);
            break;
        case 1:
            (r = q), (g = v), (b = p);
            break;
        case 2:
            (r = p), (g = v), (b = t);
            break;
        case 3:
            (r = p), (g = q), (b = v);
            break;
        case 4:
            (r = t), (g = p), (b = v);
            break;
        case 5:
            (r = v), (g = p), (b = q);
            break;
    }

    const to_hex = (n: number) => {
        var str = Math.round(n * 255).toString(16);
        return str.length == 1 ? "0" + str : str;
    };

    return `#${to_hex(r!)}${to_hex(g!)}${to_hex(b!)}`;
}

const STATUS_LOOKUP: { [key in ConnectionStatus]: [string, string] } = {
    disconnected: ["Disconnected", "alert-danger"],
    connecting: ["Connecting...", "alert-warning"],
    initialSyncing: ["Synchronizing...", "alert-warning"],
    syncing: ["Synchronizing...", "alert-warning"],
    idle: ["Connected, changes saved automatically", "alert-success"],
    error: ["Could not save data - refresh page and try again", "alert-danger"],
};

export function ConnectionStatus(props: { status: ConnectionStatus }) {
    const [text, cls] = STATUS_LOOKUP[props.status];
    return (
        <div className={"collab-connection-status alert " + cls}>
            <small className="form-text text-muted">{text}</small>
        </div>
    );
}
