import ReactModal from "react-modal";
import { createRoot, Root } from "react-dom/client";
import { useState } from "react";
import ErrorBoundary from "../../error_boundary";
import NoteTreeView from "./NoteTreeView";
import NoteEditor from "./NoteEditor";

function ProjectCollabNotesContainer() {
    const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);

    // Get project ID from page
    const projectId = parseInt(
        document.getElementById("yjs-object-id")!.innerHTML
    );

    return (
        <div
            className="collab-notes-container d-flex"
            style={{ height: "600px" }}
        >
            {/* Tree View Panel */}
            <div
                className="collab-notes-tree border-end"
                style={{
                    width: "300px",
                    minWidth: "250px",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                <NoteTreeView
                    projectId={projectId}
                    selectedId={selectedNoteId}
                    onSelect={setSelectedNoteId}
                />
            </div>

            {/* Editor Panel */}
            <div
                className="collab-notes-editor flex-grow-1"
                style={{ overflow: "auto" }}
            >
                {selectedNoteId ? (
                    <div className="p-3">
                        <NoteEditor
                            noteId={selectedNoteId}
                            key={selectedNoteId}
                        />
                    </div>
                ) : (
                    <div className="d-flex align-items-center justify-content-center h-100 text-muted">
                        <div className="text-center">
                            <i
                                className="fas fa-file-alt fa-3x mb-3"
                                style={{ opacity: 0.3 }}
                            ></i>
                            <p>Select a note to edit, or create a new one.</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

document.addEventListener("DOMContentLoaded", () => {
    ReactModal.setAppElement(
        document.querySelector("div.wrapper") as HTMLElement
    );

    const $ = (window as any).$;
    let root: Root | null = null;

    $("#id_collab_notes").on("shown.bs.tab", () => {
        if (root !== null) return;
        root = createRoot(document.getElementById("collab_notes_container")!);
        root.render(
            <ErrorBoundary>
                <ProjectCollabNotesContainer />
            </ErrorBoundary>
        );
    });

    $("#id_collab_notes").on("hidden.bs.tab", () => {
        if (root !== null) root.unmount();
        root = null;
    });
});
