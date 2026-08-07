import { expect, test } from "@playwright/test";
import * as Y from "yjs";

import { setSaveError } from "../../src/collab_server/save_error";

test("collab save-error state emits updates only when it changes", () => {
    const document = new Y.Doc();
    const serverInfo = document.get("serverInfo", Y.Map);
    serverInfo.set("saveError", false);

    let updateCount = 0;
    document.on("update", () => {
        updateCount += 1;
    });

    setSaveError(document, false);
    expect(updateCount).toBe(0);

    setSaveError(document, true);
    setSaveError(document, true);
    expect(updateCount).toBe(1);

    setSaveError(document, false);
    setSaveError(document, false);
    expect(updateCount).toBe(2);
});
