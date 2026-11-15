import { useQuery } from "@apollo/client";
import { gql } from "../../__generated__/";
import { useCallback, useMemo } from "react";
import {
    Evidence,
    EvidenceImage,
    Evidences,
    EvidencesContext,
    ReportWidthUnit,
} from "../../tiptap_gw/evidence";
import { Evidence_Bool_Exp } from "../../__generated__/graphql";
import { parseEvidenceReportId } from "./evidence_metadata";
import { getCsrfToken } from "../../services/csrf";

const QUERY_EVIDENCE = gql(`
    query QUERY_EVIDENCE($where: evidence_bool_exp!) {
        evidence(where:$where) {
            id, caption, description, friendlyName, document, reportWidthUnit, reportWidthValue
        }
    }
`);

function getPageElementText(id: string): string | null {
    const element = document.getElementById(id);
    const value = element?.textContent?.trim();
    if (!value) {
        console.error(`Missing required page metadata: #${id}`);
        return null;
    }
    return value;
}

function getPageEvidenceReportId(): number | null {
    const value = getPageElementText("graphql-evidence-report-id");
    if (value === null) return null;

    const reportId = parseEvidenceReportId(value);
    if (reportId === null) {
        console.error(
            `Invalid #graphql-evidence-report-id value: ${JSON.stringify(value)}`
        );
        return null;
    }
    return reportId;
}

export function usePageEvidence(): Evidences | null {
    const reportId = useMemo(getPageEvidenceReportId, []);
    const filters: Evidence_Bool_Exp | null = useMemo(() => {
        if (reportId === null) return null;
        return {
            reportId: { _eq: reportId },
        };
    }, [reportId]);

    const { data, refetch } = useQuery(QUERY_EVIDENCE, {
        variables: {
            where: filters ?? {},
        },
        pollInterval: 10000,
        skip: filters === null,
    });

    const getLatestImage = useCallback(
        (id: number) =>
            loadLatestEvidenceImage(id, async () => {
                const latest = await refetch();
                return latest.data.evidence;
            }),
        [refetch]
    );

    const poll = useCallback(() => refetch().then(() => {}), [refetch]);

    const refreshAfterSave = useCallback(async () => {
        try {
            await poll();
        } catch {
            // The write already succeeded. Reporting a failed save here would
            // encourage retrying a destructive image edit against its result.
            console.warn(
                "Evidence saved, but its preview could not be refreshed."
            );
        }
    }, [poll]);

    const updateCaption = useCallback(
        async (id: number, caption: string) => {
            await postEvidenceChange(
                `/reporting/reports/evidence/caption/${id}`,
                JSON.stringify({ caption }),
                "application/json"
            );
            await refreshAfterSave();
        },
        [refreshAfterSave]
    );

    const replaceImage = useCallback(
        async (id: number, image: Blob, expectedDocument: string) => {
            const body = new FormData();
            body.append("document", image, "edited.png");
            body.append("expected_document", expectedDocument);
            await postEvidenceChange(
                `/reporting/reports/evidence/image/${id}`,
                body
            );
            await refreshAfterSave();
        },
        [refreshAfterSave]
    );

    const updateReportSize = useCallback(
        async (id: number, unit: ReportWidthUnit, value: number | null) => {
            await postEvidenceChange(
                `/reporting/reports/evidence/size/${id}`,
                JSON.stringify({ unit, value }),
                "application/json"
            );
            await refreshAfterSave();
        },
        [refreshAfterSave]
    );

    const evidences = data?.evidence;
    if (evidences === null || evidences === undefined) return null;

    const uploadUrl = getPageElementText("graphql-evidence-upload-url");
    if (uploadUrl === null) return null;

    return {
        evidence: evidences,
        uploadUrl,
        poll,
        updateCaption,
        replaceImage,
        getLatestImage,
        updateReportSize,
    };
}

/** Fetch a current revision and its matching bytes before opening an editor. */
export async function loadLatestEvidenceImage(
    id: number,
    readLatest: () => Promise<readonly Evidence[]>
): Promise<EvidenceImage> {
    // A replacement between the metadata and download requests is harmless:
    // the guarded download rejects that revision and we fetch the current one.
    for (let attempt = 0; attempt < 2; attempt++) {
        const latest = (await readLatest()).find((entry) => entry.id === id);
        if (!latest) throw new Error("This evidence is no longer available.");
        if (!/\.(png|jpe?g)$/i.test(latest.document)) {
            throw new Error("This evidence is no longer a PNG or JPEG image.");
        }
        const evidence = { ...latest };
        const parameters = new URLSearchParams({
            expected_document: evidence.document,
        });
        const response = await fetch(
            `/reporting/evidence/download/${id}?${parameters}`,
            { cache: "no-store" }
        );
        if (response.status === 409) continue;
        if (
            response.redirected ||
            !response.ok ||
            !/^image\/(png|jpeg)(?:;|$)/i.test(
                response.headers.get("Content-Type") ?? ""
            )
        ) {
            throw new Error(
                "Could not load the latest image. Check your connection and sign-in, then try opening it again."
            );
        }
        return { evidence, source: await response.blob() };
    }
    throw new Error(
        "This image changed while opening. Try opening it again to load the latest version."
    );
}

export async function postEvidenceChange(
    url: string,
    body: BodyInit,
    contentType?: string
): Promise<void> {
    // Signing in again rotates Django's CSRF cookie while an open editor keeps
    // its old meta token. Prefer the fresh cookie, with DOM fallback for HttpOnly.
    const csrf =
        document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] ??
        getCsrfToken();
    if (!csrf) {
        throw new Error("CSRF token not found. Please refresh the page.");
    }
    const headers = new Headers();
    headers.append("Accept", "application/json");
    headers.append("X-CSRFToken", csrf);
    if (contentType) headers.append("Content-Type", contentType);

    const res = await fetch(url, { method: "POST", headers, body });
    const isJson = res.headers
        .get("Content-Type")
        ?.toLowerCase()
        .includes("application/json");
    // Django redirects an expired login session to an HTML login page. Fetch
    // follows that redirect, so checking status alone would discard unsaved edits.
    if (res.redirected || res.status === 401 || (res.ok && !isJson)) {
        throw new Error(
            "The server did not confirm the change. Your session may have expired. Sign in again in another tab, then retry saving."
        );
    }
    if (res.ok) return;

    let message = "Could not save the change.";
    if (res.status === 403) {
        message = "You do not have permission to edit this evidence.";
    } else if (res.status === 413) {
        message =
            "The edited image is too large to upload. Crop it to a smaller area or ask an administrator to increase the upload limit.";
    } else if (res.status === 503) {
        message =
            "The server is temporarily unavailable. Keep this editor open and retry saving when the service is restored.";
    } else if (res.status === 400 || res.status === 409) {
        // Django-style errors: { field: ["message", ...] }
        const errors: Record<string, string[]> = await res
            .json()
            .catch(() => ({}));
        const first = Object.values(errors).flat()[0];
        if (first) message = first;
    }
    throw new Error(message);
}

export function ProvidePageEvidence({
    children,
}: {
    children: React.ReactNode;
}) {
    const evidence = usePageEvidence();
    return (
        <EvidencesContext.Provider value={evidence}>
            {children}
        </EvidencesContext.Provider>
    );
}
