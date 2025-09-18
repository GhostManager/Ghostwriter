/* eslint-disable */
import * as types from './graphql.js';
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';

/**
 * Map of all GraphQL operations in the project.
 *
 * This map has several performance disadvantages:
 * 1. It is not tree-shakeable, so it will include all operations in the project.
 * 2. It is not minifiable, so the string of a GraphQL query will be multiple times inside the bundle.
 * 3. It does not support dead code elimination, so it will add unused operations.
 *
 * Therefore it is highly recommended to use the babel or swc plugin for production.
 * Learn more about it here: https://the-guild.dev/graphql/codegen/plugins/presets/preset-client#reducing-bundle-size
 */
type Documents = {
    "\n    query GET_FINDING($id: bigint!) {\n        finding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            extraFields\n        }\n        tags(model: \"finding\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n": typeof types.Get_FindingDocument,
    "\n    mutation SET_FINDING(\n        $id:bigint!,\n        $set:finding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_finding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"finding\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": typeof types.Set_FindingDocument,
    "\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n": typeof types.Get_ObservationDocument,
    "\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": typeof types.Set_ObservationDocument,
    "\n    query GET_PROJECT($id: bigint!) {\n        project_by_pk(id: $id) {\n            collab_note\n        }\n    }\n": typeof types.Get_ProjectDocument,
    "\n    mutation SET_PROJECT($id: bigint!, $collabNote:String!) {\n        update_project_by_pk(pk_columns:{id:$id}, _set:{collab_note: $collabNote}) {\n            id\n        }\n    }\n": typeof types.Set_ProjectDocument,
    "\n    query GET_REPORT($id: bigint!) {\n        report_by_pk(id: $id) {\n            extraFields\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Report\"}}){\n            internalName, type\n        }\n    }\n": typeof types.Get_ReportDocument,
    "\n    mutation evi($id: bigint!, $extraFields:jsonb!) {\n        update_report_by_pk(pk_columns:{id:$id}, _set:{extraFields: $extraFields}) {\n            id\n        }\n    }\n": typeof types.EviDocument,
    "\n    query GET_REPORT_FINDING_LINK($id: bigint!) {\n        reportedFinding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            affectedEntities,\n            extraFields\n        }\n        tags(model: \"report_finding_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n": typeof types.Get_Report_Finding_LinkDocument,
    "\n    mutation SET_REPORT_FINDING_LINK(\n        $id:bigint!,\n        $set:reportedFinding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_reportedFinding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"report_finding_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": typeof types.Set_Report_Finding_LinkDocument,
    "\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n": typeof types.Get_Report_Observation_LinkDocument,
    "\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": typeof types.Set_Report_Observation_LinkDocument,
    "\n    query GET_FINDING_TYPES {\n        findingType(order_by:[{id: asc}]) {\n            id, findingType\n        }\n    }\n": typeof types.Get_Finding_TypesDocument,
    "\n    query GET_SEVERITIES {\n        findingSeverity(order_by:[{id: asc}]) {\n            id, severity\n        }\n    }\n": typeof types.Get_SeveritiesDocument,
    "\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n": typeof types.Query_EvidenceDocument,
};
const documents: Documents = {
    "\n    query GET_FINDING($id: bigint!) {\n        finding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            extraFields\n        }\n        tags(model: \"finding\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n": types.Get_FindingDocument,
    "\n    mutation SET_FINDING(\n        $id:bigint!,\n        $set:finding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_finding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"finding\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": types.Set_FindingDocument,
    "\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n": types.Get_ObservationDocument,
    "\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": types.Set_ObservationDocument,
    "\n    query GET_PROJECT($id: bigint!) {\n        project_by_pk(id: $id) {\n            collab_note\n        }\n    }\n": types.Get_ProjectDocument,
    "\n    mutation SET_PROJECT($id: bigint!, $collabNote:String!) {\n        update_project_by_pk(pk_columns:{id:$id}, _set:{collab_note: $collabNote}) {\n            id\n        }\n    }\n": types.Set_ProjectDocument,
    "\n    query GET_REPORT($id: bigint!) {\n        report_by_pk(id: $id) {\n            extraFields\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Report\"}}){\n            internalName, type\n        }\n    }\n": types.Get_ReportDocument,
    "\n    mutation evi($id: bigint!, $extraFields:jsonb!) {\n        update_report_by_pk(pk_columns:{id:$id}, _set:{extraFields: $extraFields}) {\n            id\n        }\n    }\n": types.EviDocument,
    "\n    query GET_REPORT_FINDING_LINK($id: bigint!) {\n        reportedFinding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            affectedEntities,\n            extraFields\n        }\n        tags(model: \"report_finding_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n": types.Get_Report_Finding_LinkDocument,
    "\n    mutation SET_REPORT_FINDING_LINK(\n        $id:bigint!,\n        $set:reportedFinding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_reportedFinding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"report_finding_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": types.Set_Report_Finding_LinkDocument,
    "\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n": types.Get_Report_Observation_LinkDocument,
    "\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": types.Set_Report_Observation_LinkDocument,
    "\n    query GET_FINDING_TYPES {\n        findingType(order_by:[{id: asc}]) {\n            id, findingType\n        }\n    }\n": types.Get_Finding_TypesDocument,
    "\n    query GET_SEVERITIES {\n        findingSeverity(order_by:[{id: asc}]) {\n            id, severity\n        }\n    }\n": types.Get_SeveritiesDocument,
    "\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n": types.Query_EvidenceDocument,
};

/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 *
 *
 * @example
 * ```ts
 * const query = gql(`query GetUser($id: ID!) { user(id: $id) { name } }`);
 * ```
 *
 * The query argument is unknown!
 * Please regenerate the types.
 */
export function gql(source: string): unknown;

/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_FINDING($id: bigint!) {\n        finding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            extraFields\n        }\n        tags(model: \"finding\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_FINDING($id: bigint!) {\n        finding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            extraFields\n        }\n        tags(model: \"finding\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_FINDING(\n        $id:bigint!,\n        $set:finding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_finding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"finding\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"): (typeof documents)["\n    mutation SET_FINDING(\n        $id:bigint!,\n        $set:finding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_finding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"finding\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"): (typeof documents)["\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_PROJECT($id: bigint!) {\n        project_by_pk(id: $id) {\n            collab_note\n        }\n    }\n"): (typeof documents)["\n    query GET_PROJECT($id: bigint!) {\n        project_by_pk(id: $id) {\n            collab_note\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_PROJECT($id: bigint!, $collabNote:String!) {\n        update_project_by_pk(pk_columns:{id:$id}, _set:{collab_note: $collabNote}) {\n            id\n        }\n    }\n"): (typeof documents)["\n    mutation SET_PROJECT($id: bigint!, $collabNote:String!) {\n        update_project_by_pk(pk_columns:{id:$id}, _set:{collab_note: $collabNote}) {\n            id\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_REPORT($id: bigint!) {\n        report_by_pk(id: $id) {\n            extraFields\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Report\"}}){\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_REPORT($id: bigint!) {\n        report_by_pk(id: $id) {\n            extraFields\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Report\"}}){\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation evi($id: bigint!, $extraFields:jsonb!) {\n        update_report_by_pk(pk_columns:{id:$id}, _set:{extraFields: $extraFields}) {\n            id\n        }\n    }\n"): (typeof documents)["\n    mutation evi($id: bigint!, $extraFields:jsonb!) {\n        update_report_by_pk(pk_columns:{id:$id}, _set:{extraFields: $extraFields}) {\n            id\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_REPORT_FINDING_LINK($id: bigint!) {\n        reportedFinding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            affectedEntities,\n            extraFields\n        }\n        tags(model: \"report_finding_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_REPORT_FINDING_LINK($id: bigint!) {\n        reportedFinding_by_pk(id: $id) {\n            title,\n            description,\n            impact,\n            mitigation,\n            replication_steps,\n            hostDetectionTechniques,\n            networkDetectionTechniques,\n            references,\n            findingGuidance,\n            cvssScore,\n            cvssVector,\n            severity { id },\n            findingTypeId,\n            affectedEntities,\n            extraFields\n        }\n        tags(model: \"report_finding_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Finding\"}}) {\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_REPORT_FINDING_LINK(\n        $id:bigint!,\n        $set:reportedFinding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_reportedFinding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"report_finding_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"): (typeof documents)["\n    mutation SET_REPORT_FINDING_LINK(\n        $id:bigint!,\n        $set:reportedFinding_set_input!,\n        $tags:[String!]!,\n    ) {\n        update_reportedFinding_by_pk(pk_columns:{id:$id}, _set:$set) {\n            id\n        }\n        setTags(model: \"report_finding_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"): (typeof documents)["\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_FINDING_TYPES {\n        findingType(order_by:[{id: asc}]) {\n            id, findingType\n        }\n    }\n"): (typeof documents)["\n    query GET_FINDING_TYPES {\n        findingType(order_by:[{id: asc}]) {\n            id, findingType\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_SEVERITIES {\n        findingSeverity(order_by:[{id: asc}]) {\n            id, severity\n        }\n    }\n"): (typeof documents)["\n    query GET_SEVERITIES {\n        findingSeverity(order_by:[{id: asc}]) {\n            id, severity\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n"): (typeof documents)["\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n"];

export function gql(source: string) {
  return (documents as any)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<  infer TType,  any>  ? TType  : never;