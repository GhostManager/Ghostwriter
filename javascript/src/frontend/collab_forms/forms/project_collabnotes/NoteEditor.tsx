import {
    ConnectionStatus,
    usePageConnection,
} from "../../connection";
import RichTextEditor from "../../rich_text_editor";

interface NoteEditorProps {
    noteId: number;
}

export default function NoteEditor({ noteId }: NoteEditorProps) {
    const { provider, status, connected } = usePageConnection({
        model: "project_collab_note",
        id: noteId.toString(),
    });

    return (
        <div className="note-editor-container">
            <ConnectionStatus status={status} />
            <div className="form-group">
                <RichTextEditor
                    connected={connected}
                    provider={provider}
                    fragment={provider.document.getXmlFragment("content")}
                />
            </div>
        </div>
    );
}
