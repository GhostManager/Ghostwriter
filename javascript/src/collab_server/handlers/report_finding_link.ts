import { gql } from "../../__generated__/";
import { simpleModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, tagsToYjs, yjsToHtml, yjsToTags } from "../yjs_converters";
import { extraFieldsFromYdoc, extraFieldsToYdoc } from "../extra_fields";

const GET = gql(`
    query GET_REPORT_FINDING_LINK($id: bigint!) {
        reportedFinding_by_pk(id: $id) {
            title,
            description,
            impact,
            mitigation,
            replication_steps,
            hostDetectionTechniques,
            networkDetectionTechniques,
            references,
            findingGuidance,
            cvssScore,
            cvssVector,
            severity { id },
            findingTypeId,
            affectedEntities,
            extraFields
        }
        tags(model: "report_finding_link", id: $id) {
            tags
        }
        extraFieldSpec(where:{targetModel:{_eq:"reporting.Finding"}}) {
            internalName, type
        }
    }
`);

const SET = gql(`
    mutation SET_REPORT_FINDING_LINK(
        $id:bigint!,
        $set:reportedFinding_set_input!,
        $tags:[String!]!,
    ) {
        update_reportedFinding_by_pk(pk_columns:{id:$id}, _set:$set) {
            id
        }
        setTags(model: "report_finding_link", id: $id, tags: $tags) {
            tags
        }
    }
`);

const ReportFindingLinkHandler = simpleModelHandler(
    GET,
    SET,
    (doc, res) => {
        const obj = res.reportedFinding_by_pk;
        if (!obj) throw new Error("No object");
        const plain_fields = doc.get("plain_fields", Y.Map);
        plain_fields.set("title", obj.title);
        if (obj.cvssScore !== null && obj.cvssScore !== undefined)
            plain_fields.set("cvssScore", obj.cvssScore);
        plain_fields.set("cvssVector", obj.cvssVector);
        plain_fields.set("findingTypeId", obj.findingTypeId);
        plain_fields.set("severityId", obj.severity.id);
        htmlToYjs(obj.description, doc.get("description", Y.XmlFragment));
        htmlToYjs(obj.impact, doc.get("impact", Y.XmlFragment));
        htmlToYjs(obj.mitigation, doc.get("mitigation", Y.XmlFragment));
        htmlToYjs(
            obj.replication_steps,
            doc.get("replicationSteps", Y.XmlFragment)
        );
        htmlToYjs(
            obj.hostDetectionTechniques,
            doc.get("hostDetectionTechniques", Y.XmlFragment)
        );
        htmlToYjs(
            obj.networkDetectionTechniques,
            doc.get("networkDetectionTechniques", Y.XmlFragment)
        );
        htmlToYjs(obj.references, doc.get("references", Y.XmlFragment));
        htmlToYjs(
            obj.findingGuidance,
            doc.get("findingGuidance", Y.XmlFragment)
        );
        htmlToYjs(
            obj.affectedEntities,
            doc.get("affectedEntities", Y.XmlFragment)
        );
        tagsToYjs(res.tags.tags, doc.get("tags", Y.Map<boolean>));
        extraFieldsToYdoc(res.extraFieldSpec, doc, obj.extraFields);
    },
    (doc, id) => {
        const plainFields = doc.get("plain_fields", Y.Map<any>);
        const extraFields = extraFieldsFromYdoc(doc);
        return {
            id,
            set: {
                title: plainFields.get("title") ?? "",
                cvssScore: plainFields.get("cvssScore") ?? null,
                cvssVector: plainFields.get("cvssVector") ?? "",
                findingTypeId: plainFields.get("findingTypeId"),
                severityId: plainFields.get("severityId"),

                description: yjsToHtml(doc.get("description", Y.XmlFragment)),
                impact: yjsToHtml(doc.get("impact", Y.XmlFragment)),
                mitigation: yjsToHtml(doc.get("mitigation", Y.XmlFragment)),
                replication_steps: yjsToHtml(
                    doc.get("replicationSteps", Y.XmlFragment)
                ),
                hostDetectionTechniques: yjsToHtml(
                    doc.get("hostDetectionTechniques", Y.XmlFragment)
                ),
                networkDetectionTechniques: yjsToHtml(
                    doc.get("networkDetectionTechniques", Y.XmlFragment)
                ),
                references: yjsToHtml(doc.get("references", Y.XmlFragment)),
                findingGuidance: yjsToHtml(
                    doc.get("findingGuidance", Y.XmlFragment)
                ),
                affectedEntities: yjsToHtml(
                    doc.get("affectedEntities", Y.XmlFragment)
                ),
            },
            tags: yjsToTags(doc.get("tags", Y.Map<boolean>)),
            extraFields,
        };
    }
);
export default ReportFindingLinkHandler;
