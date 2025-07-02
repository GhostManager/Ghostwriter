import {
    Editor,
    EditorProvider,
    useCurrentEditor,
    useEditor,
    useEditorState,
} from "@tiptap/react";
import EXTENSIONS from "../tiptap_gw";
import { Toolbar } from "./collab_forms/rich_text_editor";
import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

function RichTextEditor(props: { name: string; initial: string; id: string }) {
    return (
        <div className="collab-editor">
            <EditorProvider
                extensions={EXTENSIONS}
                slotBefore={<Toolbar />}
                content={props.initial}
            >
                <HtmlInputElement
                    name={props.name}
                    initial={props.initial}
                    id={props.id}
                />
            </EditorProvider>
        </div>
    );
}

function HtmlInputElement(props: {
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

    const { editor } = useCurrentEditor();
    useEffect(() => {
        editor?.on("update", updateHtml);
        return () => {
            editor?.off("update", updateHtml);
        };
    }, [editor]);

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
