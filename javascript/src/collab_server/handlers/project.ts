import { gql } from "../../__generated__";
import { simpleModelHandler } from "../base_handler";
import * as Y from "yjs";
import { htmlToYjs, yjsToHtml } from "../yjs_converters";

const GET = gql(`
    query GET_PROJECT($id: bigint!) {
        project_by_pk(id: $id) {
            collab_note
        }
    }
`);

const SET = gql(`
    mutation SET_PROJECT($id: bigint!, $collabNote:String!) {
        update_project_by_pk(pk_columns:{id:$id}, _set:{collab_note: $collabNote}) {
            id
        }
    }
`);

const ProjectCollabNoteHandler = simpleModelHandler(
    GET,
    SET,
    (doc, res) => {
        const obj = res.project_by_pk;
        if (!obj) throw new Error("No object");
        htmlToYjs(obj.collab_note, doc.get("collabNote", Y.XmlFragment));
        return null;
    },
    (doc, id, _: null) => {
        return {
            id,
            collabNote: yjsToHtml(doc.get("collabNote", Y.XmlFragment)),
        };
    }
);
export default ProjectCollabNoteHandler;
