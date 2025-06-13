import { useQuery } from "@apollo/client";
import { gql } from "../../__generated__/";
import { Evidence_Bool_Exp } from "../../__generated__/graphql";
import { useCallback, useMemo } from "react";
import { Evidences, EvidencesContext } from "../../tiptap_gw/evidence";

const QUERY_EVIDENCE = gql(`
    query QUERY_EVIDENCE($where: evidence_bool_exp!) {
        evidence(where:$where) {
            id, caption, description, friendlyName, document
        }
    }
`);

export function usePageEvidence(): Evidences | null {
    const filters: Evidence_Bool_Exp["_or"] = useMemo(() => {
        const reportId = parseInt(
            document.getElementById("graphql-evidence-report-id")!.innerHTML
        );
        const findingIdText = document.getElementById(
            "graphql-evidence-finding-id"
        )?.innerHTML;
        const filters: Evidence_Bool_Exp["_or"] = [
            {
                report_id: { _eq: reportId },
            },
        ];
        if (findingIdText !== undefined) {
            filters.push({
                findingId: { _eq: +findingIdText },
            });
        }
        return filters;
    }, []);

    const { data, refetch } = useQuery(QUERY_EVIDENCE, {
        variables: {
            where: {
                _or: filters,
            },
        },
        pollInterval: 10000,
    });

    const poll = useCallback(() => refetch().then(() => {}), [refetch]);

    const evidences = data?.evidence;
    if (evidences === null || evidences === undefined) return null;

    const mediaUrl = document.getElementById("graphql-media-url")!.innerHTML;
    const uploadUrl = document.getElementById(
        "graphql-evidence-upload-url"
    )!.innerHTML;

    return {
        evidence: evidences,
        mediaUrl,
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
