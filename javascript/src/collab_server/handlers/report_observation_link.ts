import { gql } from "../../__generated__/";
import { ModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, tagsToYjs, yjsToHtml, yjsToTags } from "../yjs_converters";
import { extraFieldsFromYdoc, extraFieldsToYdoc } from "../extra_fields";

const GET = gql(`
    query GET_REPORT_OBSERVATION_LINK($id: bigint!) {
        reporting_reportobservationlink_by_pk(id: $id) {
            title, description, extraFields
        }
        tags(model: "report_observation_link", id: $id) {
            tags
        }
        extraFieldSpec(where:{targetModel:{_eq:"reporting.ReportObservationLink"}}) {
            internalName, type
        }
    }
`);

const SET = gql(`
    mutation SET_REPORT_OBSERVATION_LINK(
        $id:bigint!,
        $title:String!,
        $description:String!,
        $tags:[String!]!,
        $extraFields:jsonb!,
    ) {
        update_reporting_reportobservationlink_by_pk(pk_columns:{id:$id}, _set:{
            title: $title,
            description: $description,
            extraFields: $extraFields,
        }) {
            id
        }
        setTags(model: "report_observation_link", id: $id, tags: $tags) {
            tags
        }
    }
`);

export default class ReportObservationLinkHandler extends ModelHandler {
    async load(): Promise<Y.Doc> {
        const res = await this.client.query({
            query: GET,
            variables: {
                id: this.id,
            },
        });
        if (res.error || res.errors) {
            throw res.error || res.errors;
        }
        const obj = res.data.reporting_reportobservationlink_by_pk;
        if (!obj) throw new Error("No object");

        const doc = new Y.Doc();

        doc.transact(() => {
            const plain_fields = doc.get("plain_fields", Y.Map);
            plain_fields.set("title", obj.title);
            htmlToYjs(obj.description, doc.get("description", Y.XmlFragment));
            tagsToYjs(res.data.tags.tags, doc.get("tags", Y.Map<boolean>));
            extraFieldsToYdoc(res.data.extraFieldSpec, doc, obj.extraFields);
        });

        return doc;
    }

    async save(doc: Y.Doc): Promise<void> {
        let mutate_promise;
        doc.transact(() => {
            const plainFields = doc.get("plain_fields", Y.Map);
            const extraFields = extraFieldsFromYdoc(doc);
            mutate_promise = this.client.mutate({
                mutation: SET,
                variables: {
                    id: this.id,
                    title:
                        (plainFields.get("title") as string | undefined) ?? "",
                    description: yjsToHtml(
                        doc.get("description", Y.XmlFragment)
                    ),
                    tags: yjsToTags(doc.get("tags", Y.Map<boolean>)),
                    extraFields,
                },
            });
        });
        const res = await mutate_promise!;
        if (res.error || res.errors) {
            throw res.error || res.errors;
        }
    }
}
