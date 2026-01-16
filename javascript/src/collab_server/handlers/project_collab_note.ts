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
        }
    }
`);

const SET = gql(`
    mutation SET_PROJECT_COLLAB_NOTE($id: bigint!, $content: String!) {
        update_projectCollabNote_by_pk(
            pk_columns: {id: $id},
            _set: {content: $content}
        ) {
            id
        }
    }
`);

const ProjectCollabNoteItemHandler = simpleModelHandler(
    GET,
    SET,
    (doc, res) => {
        const obj = res.projectCollabNote_by_pk;
        if (!obj) throw new Error("No object");
        if (obj.nodeType !== "note") {
            throw new Error("Cannot edit folder content");
        }

        htmlToYjs(obj.content, doc.get("content", Y.XmlFragment));

        // Store title in meta for display (read-only in editor)
        const meta = doc.get("meta", Y.Map);
        meta.set("title", obj.title);

        return null;
    },
    (doc, id, _: null) => {
        return {
            id,
            content: yjsToHtml(doc.get("content", Y.XmlFragment)),
        };
    }
);

export default ProjectCollabNoteItemHandler;
