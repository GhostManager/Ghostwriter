export function parseEvidenceReportId(value: string | null): number | null {
    if (value === null || value === "") return null;

    if (!/^\d+$/.test(value)) {
        return null;
    }

    const reportId = Number(value);
    return Number.isSafeInteger(reportId) ? reportId : null;
}
