import { type ModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, yjsToHtml } from "../yjs_converters";
import { ApolloClient, gql as rawGql } from "@apollo/client/core";

interface FieldData {
    id: string;
    fieldType: string;
    image: string | null;
    position: number;
}

const GET_QUERY = rawGql`
    query GET_PROJECT_COLLAB_NOTE($id: bigint!) {
        projectCollabNote_by_pk(id: $id) {
            content
            title
            nodeType
            fields(order_by: {position: asc}) {
                id
                fieldType
                content
                image
                position
            }
        }
    }
`;

const SET_MUTATION = rawGql`
    mutation SET_PROJECT_COLLAB_NOTE_FIELDS($updates: [projectCollabNoteField_updates!]!) {
        update_projectCollabNoteField_many(updates: $updates) {
            affected_rows
        }
    }
`;

const ProjectCollabNoteItemHandler: ModelHandler<FieldData[]> = {
    async load(client: ApolloClient<unknown>, id: number) {
        const res = await client.query({
            query: GET_QUERY,
            variables: { id },
        });
        if (res.error || res.errors) throw res.error || res.errors;

        const obj = res.data.projectCollabNote_by_pk;
        if (!obj) throw new Error("No object");
        if (obj.nodeType !== "note") throw new Error("Cannot edit folder content");

        const doc = new Y.Doc();
        let fieldDataArr: FieldData[];

        doc.transact(() => {
            const meta = doc.get("meta", Y.Map);
            meta.set("title", obj.title);

            const fieldsArray = new Y.Array<FieldData>();

            if (obj.fields.length === 0 && obj.content) {
                const legacyField: FieldData = {
                    id: "legacy",
                    fieldType: "rich_text",
                    image: null,
                    position: 0,
                };
                fieldsArray.push([legacyField]);
                htmlToYjs(obj.content, doc.get("field_legacy", Y.XmlFragment));
                fieldDataArr = [legacyField];
            } else {
                fieldDataArr = obj.fields.map((field: any) => {
                    const imageUrl = field.image ? `/media/${field.image}` : null;
                    const fieldData: FieldData = {
                        id: field.id.toString(),
                        fieldType: field.fieldType,
                        image: imageUrl,
                        position: field.position,
                    };
                    fieldsArray.push([fieldData]);

                    if (field.fieldType === "rich_text") {
                        htmlToYjs(
                            field.content,
                            doc.get(`field_${field.id}`, Y.XmlFragment)
                        );
                    }
                    return fieldData;
                });
            }

            meta.set("fields", fieldsArray);
        });

        return [doc, fieldDataArr!];
    },

    async save(client: ApolloClient<unknown>, id: number, doc: Y.Doc, _data: FieldData[]) {
        let queryVars: any;
        doc.transact(() => {
            const meta = doc.get("meta", Y.Map) as Y.Map<unknown>;
            const fieldsArray = meta.get("fields") as Y.Array<FieldData> | undefined;

            if (!fieldsArray) {
                queryVars = { updates: [] };
                return;
            }

            const currentFields: FieldData[] = [];
            for (let i = 0; i < fieldsArray.length; i++) {
                currentFields.push(fieldsArray.get(i));
            }

            const updates = currentFields
                .filter((f) => f.fieldType === "rich_text" && f.id !== "legacy")
                .map((f) => ({
                    where: { id: { _eq: parseInt(f.id) } },
                    _set: {
                        content: yjsToHtml(
                            doc.get(`field_${f.id}`, Y.XmlFragment)
                        ),
                    },
                }));
            queryVars = { updates };
        });

        if (queryVars.updates.length > 0) {
            const res = await client.mutate({
                mutation: SET_MUTATION,
                variables: queryVars,
            });
            if (res.errors) throw res.errors;
        }
    },
};

export default ProjectCollabNoteItemHandler;
