import * as Y from "yjs";

/** Update the shared save-error flag only when its value has changed. */
export function setSaveError(document: Y.Doc, value: boolean): void {
    const serverInfo = document.get("serverInfo", Y.Map);
    if (serverInfo.get("saveError") === value) return;

    document.transact(() => {
        serverInfo.set("saveError", value);
    });
}
