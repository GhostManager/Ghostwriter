import { Editor, useEditorState } from "@tiptap/react";
import { MenuItem } from "@szhsin/react-menu";

export default function TextExpansionButton({ editor }: { editor: Editor }) {
    const enabled = useEditorState({
        editor,
        selector: ({ editor }) => editor.can().expandAcronym(),
    });

    return (
        <MenuItem
            title="Expand Acronyms (Ctrl+E / Cmd+E)"
            disabled={!enabled}
            onClick={() => {
                editor.commands.expandAcronym();
            }}
        >
            Expand Acronyms
        </MenuItem>
    );
}
