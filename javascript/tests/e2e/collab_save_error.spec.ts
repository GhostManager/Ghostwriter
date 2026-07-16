import { expect, test } from "@playwright/test";
import * as Y from "yjs";

import { setSaveError } from "../../src/collab_server/save_error";

test.describe("collaboration save-error state", () => {
    test("emits Yjs updates only when the error state changes", () => {
        const doc = new Y.Doc();
        const serverInfo = doc.get("serverInfo", Y.Map);
        serverInfo.set("saveError", false);

        let updateCount = 0;
        doc.on("update", () => {
            updateCount += 1;
        });

        setSaveError(doc, false);
        expect(updateCount).toBe(0);

        setSaveError(doc, true);
        expect(updateCount).toBe(1);

        setSaveError(doc, true);
        expect(updateCount).toBe(1);

        setSaveError(doc, false);
        expect(updateCount).toBe(2);

        setSaveError(doc, false);
        expect(updateCount).toBe(2);
    });
});
