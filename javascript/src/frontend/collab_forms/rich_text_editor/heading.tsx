import { useState } from "react";
import { HeadingWithId } from "../../../tiptap_gw/heading";
import { Editor, useEditorState } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";
import BookmarkDialog from "./bookmark";

export default function HeadingIdButton({ editor }: { editor: Editor }) {
    const [modalOpen, setModalOpen] = useState(false);
    const [bookmark, setBookmark] = useState("");

    const enabled = useEditorState({
        editor,
        selector: ({ editor }) => {
            if (!editor.isInitialized) return false;
            return editor.can().setHeadingBookmark("example");
        },
    });

    return (
        <>
            <MenuItem
                title="Heading Bookmark"
                disabled={!enabled}
                onClick={() => {
                    setBookmark(
                        editor.getAttributes(HeadingWithId.name).bookmark || ""
                    );
                    setModalOpen(true);
                }}
            >
                Set Bookmark
            </MenuItem>
            <BookmarkDialog
                isOpen={modalOpen}
                target="heading"
                bookmark={bookmark}
                setBookmark={setBookmark}
                onSave={(value) => {
                    editor.chain().setHeadingBookmark(value).run();
                }}
                onClose={() => setModalOpen(false)}
            />
        </>
    );
}
