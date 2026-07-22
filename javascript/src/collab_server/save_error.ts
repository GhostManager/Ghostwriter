import * as Y from "yjs";

/** Update the shared save-error flag only when its value has changed. */
export function setSaveError(doc: Y.Doc, value: boolean): void {
    const serverInfo = doc.get("serverInfo", Y.Map);

    // Avoid generating another Yjs update when the error state is unchanged.
    // Hocuspocus stores document updates, so redundant writes can create a
    // feedback loop when this flag is set from its own storage callback.
    if (serverInfo.get("saveError") === value) {
        return;
    }

    doc.transact(() => {
        serverInfo.set("saveError", value);
    });
}
