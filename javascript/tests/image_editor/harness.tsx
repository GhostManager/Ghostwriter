import { FreshOpenFixture } from "./fresh_open_fixture";
import { EvidenceFormFixture } from "./form_fixture";
import { EvidenceImageEditor } from "../../src/frontend/evidence_image_editor";
import { postEvidenceChange } from "../../src/frontend/graphql/evidence";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import EvidenceNode from "../../src/tiptap_gw/evidence";
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactModal from "react-modal";
import ImageAnnotator from "../../src/frontend/image_annotator";
import {
    AnnotationOp,
    freezePixelate,
    renderImage,
} from "../../src/frontend/image_annotator/render";
import EvidenceUploadForm from "../../src/frontend/collab_forms/rich_text_editor/evidence/upload";
import EvidenceModal from "../../src/frontend/collab_forms/rich_text_editor/evidence/modal";
import { EvidencesContext } from "../../src/tiptap_gw/evidence";
import "../../src/frontend/collab_forms/editor.scss";

type Saved = {
    width: number;
    height: number;
    stroke: number[];
    adjacent: number[];
};
type Controls = {
    freeze: (
        source: string,
        op: Extract<AnnotationOp, { kind: "pixelate" }>
    ) => Promise<AnnotationOp>;
    redact: (source: string, ops: AnnotationOp[]) => Promise<string>;
    exported: (
        ops: AnnotationOp[],
        points: [number, number][]
    ) => Promise<{ pixels: number[][]; png: string }>;
    connected: () => void;
    change: (url: string) => Promise<void>;
    fixture: () => string;
    render: (ops: AnnotationOp[], transparent?: boolean) => Promise<Saved>;
    source: (width: number, height: number) => void;
    saveMode: "success" | "reject" | "pending";
    releaseSave: () => void;
    saved: Saved | null;
    uploaded: number | null;
    uploadPollFailure: boolean;
    savedSizes: { id: number; unit: string; value: number | null }[];
    formSubmissions: number;
};
declare global {
    interface Window {
        imageEditorTest: Controls;
    }
}

function fixture(width = 400, height = 300, transparent = false): string {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d")!;
    if (!transparent) {
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, width, height);
    }
    ctx.fillStyle = "black";
    ctx.fillRect(50, 20, 2, 60);
    return canvas.toDataURL("image/png");
}
async function image(source: string): Promise<HTMLImageElement> {
    const img = new Image();
    img.src = source;
    await img.decode();
    return img;
}
async function inspect(blob: Blob): Promise<Saved> {
    const url = URL.createObjectURL(blob);
    try {
        const img = await image(url);
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext("2d")!;
        ctx.drawImage(img, 0, 0);
        return {
            width: canvas.width,
            height: canvas.height,
            stroke: [...ctx.getImageData(50, 30, 1, 1).data],
            adjacent: [...ctx.getImageData(52, 30, 1, 1).data],
        };
    } finally {
        URL.revokeObjectURL(url);
    }
}
const api: Controls = {
    freeze: async (source, op) =>
        freezePixelate(op, renderImage(await image(source), []), null),
    redact: async (source, ops) =>
        renderImage(await image(source), ops, true).toDataURL("image/png"),
    exported: async (ops, points) => {
        const canvas = renderImage(await image(fixture(200, 100)), ops, true);
        const png = canvas.toDataURL("image/png");
        const decoded = await image(png);
        const exported = document.createElement("canvas");
        exported.width = decoded.naturalWidth;
        exported.height = decoded.naturalHeight;
        const ctx = exported.getContext("2d")!;
        ctx.drawImage(decoded, 0, 0);
        return {
            png,
            pixels: points.map(([x, y]) => [
                ...ctx.getImageData(x, y, 1, 1).data,
            ]),
        };
    },
    connected: () => {},
    change: (url) =>
        postEvidenceChange(
            url,
            JSON.stringify({ caption: "Updated" }),
            "application/json"
        ),
    fixture,
    saved: null,
    uploaded: null,
    uploadPollFailure: false,
    savedSizes: [],
    formSubmissions: 0,
    saveMode: "success",
    releaseSave: () => {},
    source: () => {},
    render: async (ops, transparent = false) => {
        const input = await image(fixture(200, 100, transparent));
        const canvas = renderImage(input, ops, true);
        const blob = await new Promise<Blob>((resolve) =>
            canvas.toBlob((blob) => resolve(blob!), "image/png")
        );
        return inspect(blob);
    },
};
window.imageEditorTest = api;
ReactModal.setAppElement("#root");

function EvidenceFixture() {
    const editor = useEditor({
        extensions: [StarterKit, EvidenceNode],
        content: '<div class="richtext-evidence" data-evidence-id="1"></div>',
        editable: false,
    });
    api.connected = () => {
        editor?.setEditable(true);
    };
    return (
        <EvidencesContext.Provider
            value={{
                evidence: [
                    {
                        id: 1,
                        friendlyName: "Existing evidence",
                        caption: "Existing caption",
                        document: "proof.png",
                    },
                ],
                uploadUrl: "/test-upload",
                poll: async () => {},
                replaceImage: async () => {},
                getLatestImage: async (id) => ({
                    evidence: {
                        id,
                        friendlyName: "Existing evidence",
                        caption: "Existing caption",
                        document: "proof.png",
                    },
                    source: await (await fetch(fixture())).blob(),
                }),
                updateCaption: async () => {},
                updateReportSize: async (id, unit, value) => {
                    api.savedSizes.push({ id, unit, value });
                },
            }}
        >
            <EditorContent editor={editor} />
        </EvidencesContext.Provider>
    );
}

const refreshEvidence = async () => {
    if (api.uploadPollFailure)
        throw new Error("Fixture evidence refresh failed");
};

function UploadDialogFixture() {
    const editor = useEditor({ extensions: [StarterKit] });
    const [open, setOpen] = useState(true);
    const [file] = useState(
        () =>
            new File(
                [
                    Uint8Array.from(atob(fixture().split(",")[1]), (value) =>
                        value.charCodeAt(0)
                    ),
                ],
                "proof.png",
                { type: "image/png" }
            )
    );
    if (!editor) return null;
    return (
        <EvidencesContext.Provider
            value={{
                evidence: [],
                uploadUrl: "/test-upload",
                poll: refreshEvidence,
            }}
        >
            {open && (
                <EvidenceModal
                    editor={editor}
                    initialId={null}
                    initialFile={file}
                    setEvidenceId={(id) => {
                        api.uploaded = id;
                        setOpen(false);
                    }}
                />
            )}
        </EvidencesContext.Provider>
    );
}

function App() {
    const [source, setSource] = useState(() =>
        new URLSearchParams(location.search).has("large")
            ? fixture(
                  800,
                  500,
                  new URLSearchParams(location.search).has("transparent")
              )
            : fixture(
                  400,
                  300,
                  new URLSearchParams(location.search).has("transparent")
              )
    );
    const [open, setOpen] = useState(true);
    const [saved, setSaved] = useState<Saved | null>(null);
    api.source = (width, height) => setSource(fixture(width, height));
    const upload = new URLSearchParams(location.search).has("upload");
    const [pageInput, setPageInput] = useState<HTMLInputElement | null>(null);
    useEffect(() => {
        if (!pageInput) return;
        // Model the Django form's existing page-level clipboard handler.
        const paste = (event: ClipboardEvent) => {
            if (!event.clipboardData?.files.length) return;
            pageInput.files = event.clipboardData.files;
            pageInput.dispatchEvent(new Event("change", { bubbles: true }));
        };
        window.addEventListener("paste", paste);
        return () => window.removeEventListener("paste", paste);
    }, [pageInput]);
    if (new URLSearchParams(location.search).has("fresh-open"))
        return <FreshOpenFixture />;
    if (new URLSearchParams(location.search).has("async-form"))
        return <EvidenceFormFixture source={fixture()} />;
    if (new URLSearchParams(location.search).has("evidence-page"))
        return (
            <form
                onSubmit={(event) => {
                    event.preventDefault();
                    api.formSubmissions++;
                }}
            >
                <input ref={setPageInput} type="file" name="document" />
                <input
                    type="hidden"
                    name="document_was_edited"
                    defaultValue="false"
                />
                <input aria-label="Caption" defaultValue="Original caption" />
                {pageInput && (
                    <EvidenceImageEditor
                        input={pageInput}
                        source={fixture()}
                        filename="proof.jpg"
                    />
                )}
                <button type="submit">Save Changes</button>
            </form>
        );

    if (new URLSearchParams(location.search).has("evidence"))
        return <EvidenceFixture />;
    if (new URLSearchParams(location.search).has("upload-dialog"))
        return <UploadDialogFixture />;
    if (upload)
        return (
            <EvidencesContext.Provider
                value={{
                    evidence: [],
                    uploadUrl: "/test-upload",
                    poll: refreshEvidence,
                }}
            >
                <EvidenceUploadForm
                    onSubmit={(id) => {
                        api.uploaded = id;
                    }}
                    switchMode={() => {}}
                />
            </EvidencesContext.Provider>
        );
    return (
        <>
            {open && (
                <ImageAnnotator
                    source={source}
                    onCancel={() => setOpen(false)}
                    onSave={async (blob) => {
                        if (api.saveMode === "reject")
                            throw new Error("Simulated save failed");
                        if (api.saveMode === "pending")
                            await new Promise<void>((resolve) => {
                                api.releaseSave = resolve;
                            });
                        api.saved = await inspect(blob);
                        setSaved(api.saved);
                        setOpen(false);
                    }}
                />
            )}
            {saved && (
                <output aria-label="Saved image dimensions">
                    {saved.width} × {saved.height}
                </output>
            )}
        </>
    );
}
createRoot(document.getElementById("root")!).render(<App />);
