import { gql } from "../__generated__/";
import { type ModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, tagsToYjs, yjsToHtml, yjsToTags } from "../yjs_converters";
import { extraFieldsFromYdoc, extraFieldsToYdoc } from "../extra_fields";

const GET_OBSERVATION = gql(`
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

const SET_OBSERVATION = gql(`
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

const ObservationHandler: ModelHandler = {
    async load(client, id) {
        const res = await client.query({
            query: GET_OBSERVATION,
            variables: {
                id,
            },
        });
        if (res.error || res.errors) {
            throw res.error || res.errors;
        }
        const obj = res.data.reporting_observation_by_pk;
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
    },
    async save(client, id, doc) {
        let mutate_promise;
        doc.transact(() => {
            const plainFields = doc.get("plain_fields", Y.Map);
            const extraFields = extraFieldsFromYdoc(doc);
            mutate_promise = client.mutate({
                mutation: SET_OBSERVATION,
                variables: {
                    id,
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
    },
};

export default ObservationHandler;
