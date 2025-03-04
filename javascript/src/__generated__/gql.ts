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
    "\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n": typeof types.Get_ObservationDocument,
    "\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": typeof types.Set_ObservationDocument,
    "\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.ReportObservationLink\"}}) {\n            internalName, type\n        }\n    }\n": typeof types.Get_Report_Observation_LinkDocument,
    "\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": typeof types.Set_Report_Observation_LinkDocument,
    "\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n": typeof types.Query_EvidenceDocument,
};
const documents: Documents = {
    "\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n": types.Get_ObservationDocument,
    "\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": types.Set_ObservationDocument,
    "\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.ReportObservationLink\"}}) {\n            internalName, type\n        }\n    }\n": types.Get_Report_Observation_LinkDocument,
    "\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n": types.Set_Report_Observation_LinkDocument,
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
export function gql(source: "\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_OBSERVATION($id: bigint!) {\n        reporting_observation_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"observation\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.Observation\"}}) {\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"): (typeof documents)["\n    mutation SET_OBSERVATION(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"observation\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.ReportObservationLink\"}}) {\n            internalName, type\n        }\n    }\n"): (typeof documents)["\n    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {\n        reporting_reportobservationlink_by_pk(id: $id) {\n            title, description, extraFields\n        }\n        tags(model: \"report_observation_link\", id: $id) {\n            tags\n        }\n        extraFieldSpec(where:{targetModel:{_eq:\"reporting.ReportObservationLink\"}}) {\n            internalName, type\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"): (typeof documents)["\n    mutation SET_REPORT_OBSERVATION_LINK(\n        $id:bigint!,\n        $title:String!,\n        $description:String!,\n        $tags:[String!]!,\n        $extraFields:jsonb!,\n    ) {\n        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{\n            title: $title,\n            description: $description,\n            extraFields: $extraFields,\n        }) {\n            id\n        }\n        setTags(model: \"report_observation_link\", id: $id, tags: $tags) {\n            tags\n        }\n    }\n"];
/**
 * The gql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function gql(source: "\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n"): (typeof documents)["\n    query QUERY_EVIDENCE($where: evidence_bool_exp!) {\n        evidence(where:$where) {\n            id, caption, description, friendlyName, document\n        }\n    }\n"];

export function gql(source: string) {
  return (documents as any)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<  infer TType,  any>  ? TType  : never;