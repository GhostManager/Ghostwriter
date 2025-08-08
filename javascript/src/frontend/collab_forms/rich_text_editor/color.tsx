import { faPalette } from "@fortawesome/free-solid-svg-icons/faPalette";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useId, useState } from "react";
import ReactModal from "react-modal";
import { Sketch } from "@uiw/react-color";

export default function ColorButton({ editor }: { editor: Editor }) {
    const [modalMode, setModalMode] = useState<null | "new" | "edit">(null);
    const [formColor, setFormColor] = useState<string>("#f00");

    const enabled = editor
        .can()
        .chain()
        .focus()
        .setColor({ color: "#fff" })
        .run();
    const active = editor.isActive("color");

    return (
        <>
            <button
                tabIndex={-1}
                title="Color"
                type="button"
                disabled={!enabled}
                className={active ? "is-active" : undefined}
                onClick={(e) => {
                    e.preventDefault();
                    const active = editor.isActive("color");
                    if (active) {
                        editor.chain().focus().extendMarkRange("color").run();
                        setFormColor(editor.getAttributes("color").color);
                    } else {
                        setFormColor("#f00");
                    }
                    setModalMode(active ? "edit" : "new");
                }}
            >
                <FontAwesomeIcon icon={faPalette} />
            </button>
            <ReactModal
                isOpen={!!modalMode}
                onRequestClose={() => setModalMode(null)}
                contentLabel="Edit Color"
                className="modal-dialog modal-dialog-centered"
            >
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Edit Color</h5>
                    </div>
                    <div className="modal-body row justify-content-center">
                        <Sketch
                            color={formColor}
                            onChange={(color) => setFormColor(color.hex)}
                        />
                    </div>

                    <div className="modal-footer">
                        <button
                            className="btn btn-primary"
                            onClick={(e) => {
                                e.preventDefault();
                                if (formColor)
                                    editor
                                        .chain()
                                        .setColor({ color: formColor })
                                        .run();
                                setModalMode(null);
                            }}
                        >
                            Save
                        </button>
                        {modalMode === "edit" && (
                            <button
                                className="btn btn-danger"
                                onClick={(e) => {
                                    e.preventDefault();
                                    editor.chain().unsetColor().run();
                                    setModalMode(null);
                                }}
                            >
                                Remove
                            </button>
                        )}
                        <button
                            className="btn btn-secondary"
                            onClick={(e) => {
                                e.preventDefault();
                                setModalMode(null);
                            }}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </ReactModal>
        </>
    );
}
