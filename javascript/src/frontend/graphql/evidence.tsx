import { useQuery } from "@apollo/client";
import { gql } from "../../__generated__/";
import { useCallback, useMemo } from "react";
import {
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

    const poll = useCallback(() => refetch().then(() => {}), [refetch]);

    const updateCaption = useCallback(
        async (id: number, caption: string) => {
            await postEvidenceChange(
                `/reporting/reports/evidence/caption/${id}`,
                JSON.stringify({ caption }),
                "application/json"
            );
            await poll();
        },
        [poll]
    );

    const replaceImage = useCallback(
        async (id: number, image: Blob) => {
            const body = new FormData();
            body.append("document", image, "edited.png");
            await postEvidenceChange(
                `/reporting/reports/evidence/image/${id}`,
                body
            );
            await poll();
        },
        [poll]
    );

    const updateReportSize = useCallback(
        async (id: number, unit: ReportWidthUnit, value: number | null) => {
            await postEvidenceChange(
                `/reporting/reports/evidence/size/${id}`,
                JSON.stringify({ unit, value }),
                "application/json"
            );
            await poll();
        },
        [poll]
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
        updateReportSize,
    };
}

async function postEvidenceChange(
    url: string,
    body: BodyInit,
    contentType?: string
): Promise<void> {
    const csrf = getCsrfToken();
    if (!csrf) {
        throw new Error("CSRF token not found. Please refresh the page.");
    }
    const headers = new Headers();
    headers.append("Accept", "application/json");
    headers.append("X-CSRFToken", csrf);
    if (contentType) headers.append("Content-Type", contentType);

    const res = await fetch(url, { method: "POST", headers, body });
    if (res.ok) return;

    let message = "Could not save the change.";
    if (res.status === 403) {
        message = "You do not have permission to edit this evidence.";
    } else if (res.status === 400) {
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
