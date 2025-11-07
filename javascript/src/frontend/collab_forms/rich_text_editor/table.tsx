import { useId, useState } from "react";
import ReactModal from "react-modal";
import { useCurrentEditor } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";
import { GwTableCell, TableCaption } from "../../../tiptap_gw/table";
import { ColorModal, ColorModalMode } from "./color";

export function TableCaptionBookmarkButton() {
    const editor = useCurrentEditor().editor!;
    const [modalOpen, setModalOpen] = useState(false);
    const [bookmark, setBookmark] = useState("");
    const fieldId = useId();

    const enabled = editor.can().setTableCaptionBookmark("example");

    return (
        <>
            <MenuItem
                title="Caption Bookmark"
                disabled={!enabled}
                onClick={() => {
                    setBookmark(
                        editor.getAttributes(TableCaption.name).bookmark || ""
                    );
                    setModalOpen(true);
                }}
            >
                Set Bookmark
            </MenuItem>
            <ReactModal
                isOpen={modalOpen}
                onRequestClose={() => setModalOpen(false)}
                contentLabel="Edit Heading Bookmark"
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Edit Heading Bookmark</h5>
                    </div>
                    <div className="modal-body text-center">
                        <div className="form-group">
                            <label htmlFor={fieldId}>Bookmark Name</label>
                            <input
                                id={fieldId}
                                type="text"
                                className="form-control"
                                value={bookmark}
                                onChange={(e) => setBookmark(e.target.value)}
                            />
                        </div>

                        <div className="modal-footer">
                            <button
                                className="btn btn-primary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    const trimmedId = bookmark.trim();
                                    editor
                                        .chain()
                                        .setTableCaptionBookmark(
                                            trimmedId === ""
                                                ? undefined
                                                : trimmedId
                                        )
                                        .run();
                                    setModalOpen(false);
                                }}
                            >
                                Save
                            </button>
                            <button
                                className="btn btn-secondary"
                                onClick={(e) => {
                                    e.preventDefault();
                                    setModalOpen(false);
                                }}
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            </ReactModal>
        </>
    );
}

export function TableCellBackgroundColor() {
    const editor = useCurrentEditor().editor!;
    const [modalMode, setModalMode] = useState<ColorModalMode>(null);
    const [formColor, setFormColor] = useState<string>("#f00");

    const enabled = editor.can().setTableCellBackgroundColor(null);

    return (
        <>
            <MenuItem
                title="Cell Background"
                disabled={!enabled}
                onClick={(e) => {
                    const current =
                        editor.getAttributes(GwTableCell.name).bgColor || "";
                    setFormColor(current);
                    setModalMode("edit");
                }}
            >
                Cell Background
            </MenuItem>
            <ColorModal
                modalMode={modalMode}
                setModalMode={setModalMode}
                formColor={formColor}
                setFormColor={setFormColor}
                setColor={() => {
                    if (formColor)
                        editor
                            .chain()
                            .setTableCellBackgroundColor(formColor || null)
                            .run();
                }}
                removeColor={() => {
                    editor.chain().setTableCellBackgroundColor(null).run();
                }}
            />
        </>
    );
}
