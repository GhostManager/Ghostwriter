import { expect, test } from "@playwright/test";

import { parseEvidenceReportId } from "../../src/frontend/graphql/evidence_metadata";

test.describe("evidence page metadata", () => {
    test("parses numeric report ids", () => {
        expect(parseEvidenceReportId("1")).toBe(1);
        expect(parseEvidenceReportId("12345")).toBe(12345);
    });

    test("rejects missing, empty, and invalid report ids", () => {
        expect(parseEvidenceReportId(null)).toBeNull();
        expect(parseEvidenceReportId("")).toBeNull();
        expect(parseEvidenceReportId("abc")).toBeNull();
        expect(parseEvidenceReportId("123abc")).toBeNull();
        expect(parseEvidenceReportId("1.5")).toBeNull();
        expect(parseEvidenceReportId("0x10")).toBeNull();
        expect(parseEvidenceReportId("9007199254740992")).toBeNull();
    });
});
