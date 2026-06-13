import { useQuery } from "@apollo/client";
import { gql } from "../../__generated__/";
import { useCallback } from "react";
import { Evidences, EvidencesContext } from "../../tiptap_gw/evidence";

const QUERY_EVIDENCE = gql(`
    query QUERY_EVIDENCE($where: evidence_bool_exp!) {
        evidence(where:$where) {
            id, caption, description, friendlyName, document
        }
    }
`);

export function usePageEvidence(): Evidences | null {
    const { data, refetch } = useQuery(QUERY_EVIDENCE, {
        variables: {
            where: {},
        },
        pollInterval: 10000,
    });

    const poll = useCallback(() => refetch().then(() => {}), [refetch]);

    const evidences = data?.evidence;
    if (evidences === null || evidences === undefined) return null;

    const uploadUrl = document.getElementById(
        "graphql-evidence-upload-url"
    )!.innerHTML;

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
