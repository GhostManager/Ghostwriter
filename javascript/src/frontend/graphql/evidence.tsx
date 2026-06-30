import { useQuery } from "@apollo/client";
import { gql } from "../../__generated__/";
import { useCallback, useMemo } from "react";
import { Evidences, EvidencesContext } from "../../tiptap_gw/evidence";
import { Evidence_Bool_Exp } from "../../__generated__/graphql";
import { parseEvidenceReportId } from "./evidence_metadata";

const QUERY_EVIDENCE = gql(`
    query QUERY_EVIDENCE($where: evidence_bool_exp!) {
        evidence(where:$where) {
            id, caption, description, friendlyName, document
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

    const evidences = data?.evidence;
    if (evidences === null || evidences === undefined) return null;

    const uploadUrl = getPageElementText(
        "graphql-evidence-upload-url"
    );
    if (uploadUrl === null) return null;

    return {
        evidence: evidences,
        uploadUrl,
        poll,
    };
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
