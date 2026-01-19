import { gql } from "../../__generated__";
import { simpleModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, yjsToHtml } from "../yjs_converters";

const GET = gql(`
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
`);

const SET = gql(`
    mutation SET_PROJECT_COLLAB_NOTE_FIELDS($updates: [projectCollabNoteField_updates!]!) {
        update_projectCollabNoteField_many(updates: $updates) {
            affected_rows
        }
    }
`);

interface FieldData {
    id: string;
    fieldType: string;
    image: string | null;
    position: number;
}

const ProjectCollabNoteItemHandler = simpleModelHandler(
    GET,
    SET,
    (doc, res) => {
        const obj = res.projectCollabNote_by_pk;
        if (!obj) throw new Error("No object");
        if (obj.nodeType !== "note") {
            throw new Error("Cannot edit folder content");
        }

        // Store metadata about fields for frontend synchronization
        const meta = doc.get("meta", Y.Map);
        meta.set("title", obj.title);

        // Create array of field metadata
        const fieldsArray = new Y.Array<FieldData>();

        // If there are no fields but there's legacy content, create a virtual field
        if (obj.fields.length === 0 && obj.content) {
            const legacyField: FieldData = {
                id: "legacy",
                fieldType: "rich_text",
                image: null,
                position: 0
            };
            fieldsArray.push([legacyField]);
            htmlToYjs(obj.content, doc.get("field_legacy", Y.XmlFragment));
        } else {
            // Process all fields
            obj.fields.forEach((field) => {
                // Prepend /media/ to image paths from database
                const imageUrl = field.image ? `/media/${field.image}` : null;
                const fieldData: FieldData = {
                    id: field.id.toString(),
                    fieldType: field.fieldType,
                    image: imageUrl,
                    position: field.position
                };
                fieldsArray.push([fieldData]);

                // Create Yjs XmlFragment for rich_text fields only
                if (field.fieldType === "rich_text") {
                    htmlToYjs(field.content, doc.get(`field_${field.id}`, Y.XmlFragment));
                }
            });
        }

        meta.set("fields", fieldsArray);

        // Return field metadata for use in mkQueryVars
        if (obj.fields.length === 0 && obj.content) {
            return [{ id: "legacy", fieldType: "rich_text", image: null, position: 0 }];
        }
        return obj.fields.map(f => ({
            id: f.id.toString(),
            fieldType: f.fieldType,
            image: f.image ? `/media/${f.image}` : null,
            position: f.position
        }));
    },
    (doc, id, fieldData: FieldData[]) => {
        // Build updates for all rich_text fields
        const updates = fieldData
            .filter(f => f.fieldType === "rich_text")
            .map(f => ({
                where: { id: { _eq: parseInt(f.id) } },
                _set: { content: yjsToHtml(doc.get(`field_${f.id}`, Y.XmlFragment)) }
            }));
        return { updates };
    }
);

export default ProjectCollabNoteItemHandler;
