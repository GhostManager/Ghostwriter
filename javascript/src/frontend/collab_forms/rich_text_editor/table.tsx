import { useState } from "react";
import { Editor, useEditorState } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";
import { GwTableCell, TableCaption } from "../../../tiptap_gw/table";
import { ColorModal, ColorModalMode } from "./color";
import BookmarkDialog from "./bookmark";

export function TableCaptionBookmarkButton({ editor }: { editor: Editor }) {
    const [modalOpen, setModalOpen] = useState(false);
    const [bookmark, setBookmark] = useState("");

    const enabled = useEditorState({
        editor,
        selector: ({ editor }) => {
            if (!editor.isInitialized) return false;
            return editor.can().setTableCaptionBookmark("example");
        },
    });

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
            <BookmarkDialog
                isOpen={modalOpen}
                target="table caption"
                bookmark={bookmark}
                setBookmark={setBookmark}
                onSave={(value) => {
                    editor.chain().setTableCaptionBookmark(value).run();
                }}
                onClose={() => setModalOpen(false)}
            />
        </>
    );
}

export function TableCellBackgroundColor({ editor }: { editor: Editor }) {
    const [modalMode, setModalMode] = useState<ColorModalMode>(null);
    const [formColor, setFormColor] = useState<string>("#F3F5F7");

    const enabled = editor.can().setTableCellBackgroundColor(null);

    return (
        <>
            <MenuItem
                title="Cell Background"
                disabled={!enabled}
                onClick={(e) => {
                    const current =
                        editor.getAttributes(GwTableCell.name).bgColor || "";
                    setFormColor(current || "#F3F5F7");
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
                setColor={(color) => {
                    editor.chain().setTableCellBackgroundColor(color).run();
                }}
                removeColor={() => {
                    editor.chain().setTableCellBackgroundColor(null).run();
                }}
                title="Cell background"
            />
        </>
    );
}
