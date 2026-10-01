import { Editor, EditorContent, useEditor } from "@tiptap/react";
import { createGhostwriterExtensions } from "../tiptap_gw";
import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Toolbar } from "./collab_forms/rich_text_editor";

function RichTextEditor(props: { name: string; initial: string; id: string }) {
    const editor = useEditor({
        extensions: createGhostwriterExtensions({ undoRedo: true }),
        content: props.initial,
        autofocus: false,
        editorProps: {
            attributes: {
                "aria-label": "Default formatted text",
                class: "gw-tiptap-editable",
                spellcheck: "true",
            },
        },
    });

    return (
        <div className="collab-editor gw-standalone-editor gw-editor-profile-standard">
            <Toolbar editor={editor} history profile="standard" />
            <EditorContent editor={editor} />
            <HtmlInputElement
                editor={editor}
                name={props.name}
                initial={props.initial}
                id={props.id}
            />
        </div>
    );
}

function HtmlInputElement(props: {
    editor: Editor | null;
    name: string;
    initial: string;
    id: string;
}) {
    const [html, setHtml] = useState(props.initial);
    const updateHtml = useCallback(
        ({ editor }: { editor: Editor }) => {
            setHtml(editor.getHTML());
        },
        [setHtml]
    );

    useEffect(() => {
        props.editor?.on("update", updateHtml);
        return () => {
            props.editor?.off("update", updateHtml);
        };
    }, [props.editor, updateHtml]);

    return <input type="hidden" name={props.name} value={html} id={props.id} />;
}

(window as any).gwSetupTiptapEditor = (
    el: HTMLElement,
    name: string,
    id: string,
    initial: string
) => {
    const root = createRoot(el);
    root.render(<RichTextEditor name={name} id={id} initial={initial} />);
    return () => root.unmount();
};
