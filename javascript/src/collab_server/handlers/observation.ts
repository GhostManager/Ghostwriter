import { gql } from "../../__generated__/";
import { simpleModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, tagsToYjs, yjsToHtml, yjsToTags } from "../yjs_converters";
import { extraFieldsFromYdoc, extraFieldsToYdoc } from "../extra_fields";

const GET = gql(`
    query GET_OBSERVATION($id: bigint!) {
        reporting_observation_by_pk(id: $id) {
            title, description, extraFields
        }
        tags(model: "observation", id: $id) {
            tags
        }
        extraFieldSpec(where:{targetModel:{_eq:"reporting.Observation"}}) {
            internalName, type
        }
    }
`);

const SET = gql(`
    mutation SET_OBSERVATION(
        $id:bigint!,
        $title:String!,
        $description:String!,
        $tags:[String!]!,
        $extraFields:jsonb!,
    ) {
        update_reporting_observation_by_pk(pk_columns:{id:$id}, _set:{
            title: $title,
            description: $description,
            extraFields: $extraFields,
        }) {
            id
        }
        setTags(model: "observation", id: $id, tags: $tags) {
            tags
        }
    }
`);

const ObservationHandler = simpleModelHandler(
    GET,
    SET,
    (doc, res) => {
        const obj = res.reporting_observation_by_pk;
        if (!obj) throw new Error("No object");
        const plain_fields = doc.get("plain_fields", Y.Map);
        plain_fields.set("title", obj.title);
        htmlToYjs(obj.description, doc.get("description", Y.XmlFragment));
        tagsToYjs(res.tags.tags, doc.get("tags", Y.Map<boolean>));
        extraFieldsToYdoc(res.extraFieldSpec, doc, obj.extraFields);
        return res.extraFieldSpec;
    },
    (doc, id, extraFieldSpec) => {
        const plainFields = doc.get("plain_fields", Y.Map);
        const extraFields = extraFieldsFromYdoc(extraFieldSpec, doc);
        return {
            id,
            title: (plainFields.get("title") as string | undefined) ?? "",
            description: yjsToHtml(doc.get("description", Y.XmlFragment)),
            tags: yjsToTags(doc.get("tags", Y.Map<boolean>)),
            extraFields,
        };
    }
);
export default ObservationHandler;
