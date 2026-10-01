import "./standalone_tiptap.scss";

import { Editor } from "@tiptap/core";
import { EditorContent, EditorContext, useEditor } from "@tiptap/react";
import { useEffect, useMemo, useRef } from "react";
import { flushSync } from "react-dom";
import { createRoot, Root } from "react-dom/client";

import { createGhostwriterExtensions } from "../tiptap_gw";
import { Toolbar } from "./collab_forms/rich_text_editor";

export type EditorProfile = "compact" | "standard" | "narrative";

type MountedEditor = {
    editor: Editor | null;
    host: HTMLDivElement;
    root: Root;
    source: HTMLTextAreaElement;
    destroy: () => void;
    syncFromSource: () => void;
};

type InitOptions = {
    includeInactiveTabs?: boolean;
    preserveScroll?: boolean;
    skipTabPanes?: boolean;
};

const mountedEditors = new Map<HTMLTextAreaElement, MountedEditor>();

function requestFormSubmit(form: HTMLFormElement) {
    if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
    } else {
        form.dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
    }
}

function profileFor(source: HTMLTextAreaElement): EditorProfile {
    const explicitProfile = source.dataset.richTextProfile;
    if (
        explicitProfile === "compact" ||
        explicitProfile === "standard" ||
        explicitProfile === "narrative"
    ) {
        return explicitProfile;
    }
    if (source.classList.contains("gw-tiptap-compact")) {
        return "compact";
    }
    if (source.classList.contains("gw-tiptap-narrative")) {
        return "narrative";
    }
    return "standard";
}

function minimumHeightFor(
    source: HTMLTextAreaElement,
    profile: EditorProfile
): number {
    const container = source.closest<HTMLElement>("[data-tiptap-min-height]");
    const configured = container?.dataset.tiptapMinHeight;
    const parsed = configured ? Number.parseInt(configured, 10) : Number.NaN;
    if (Number.isFinite(parsed)) return parsed;
    if (profile === "compact") return 128;
    if (profile === "narrative") return 240;
    return 160;
}

function accessibleLabelFor(source: HTMLTextAreaElement): string {
    const explicit = source.getAttribute("aria-label");
    if (explicit) return explicit;
    if (source.id) {
        const label = document.querySelector<HTMLLabelElement>(
            `label[for="${CSS.escape(source.id)}"]`
        );
        const labelText = label?.textContent?.trim();
        if (labelText) return labelText;
    }
    return source.name || "Rich text";
}

function isInInactiveTab(source: HTMLTextAreaElement): boolean {
    const tabPane = source.closest(".tab-pane");
    return !!tabPane && !tabPane.classList.contains("active");
}

function isInClosedCollection(source: HTMLTextAreaElement): boolean {
    return !!source.closest("details:not([open])");
}

function shouldEnhance(
    source: HTMLTextAreaElement,
    options?: InitOptions
): boolean {
    if (
        mountedEditors.has(source) ||
        !source.isConnected ||
        source.disabled ||
        source.classList.contains("empty-form") ||
        source.classList.contains("no-auto-tiptap") ||
        source.classList.contains("no-auto-rich-text") ||
        source.closest(".empty-form, [id^='empty-form-']")
    ) {
        return false;
    }
    if (options?.skipTabPanes && source.closest(".tab-pane")) return false;
    if (!options?.includeInactiveTabs && isInInactiveTab(source)) return false;
    if (isInClosedCollection(source)) return false;
    return true;
}

function editorHtml(editor: Editor): string {
    return editor.isEmpty ? "" : editor.getHTML();
}

function StandaloneRichTextEditor(props: {
    source: HTMLTextAreaElement;
    profile: EditorProfile;
    onEditor: (editor: Editor | null) => void;
}) {
    const extensions = useMemo(
        () => createGhostwriterExtensions({ undoRedo: true }),
        []
    );
    const dirty = useRef(false);
    const source = props.source;
    const editor = useEditor({
        autofocus: false,
        content: source.value,
        editable: !source.readOnly,
        extensions,
        editorProps: {
            attributes: {
                "aria-label": accessibleLabelFor(source),
                class: "gw-tiptap-editable",
                spellcheck: "true",
            },
            handleKeyDown: (_, event) => {
                if (
                    event.key === "Enter" &&
                    (event.ctrlKey || event.metaKey) &&
                    source.closest("[data-submit-on-mod-enter]")
                ) {
                    const form = source.closest("form");
                    if (form) {
                        event.preventDefault();
                        event.stopPropagation();
                        requestFormSubmit(form);
                        return true;
                    }
                }
                return false;
            },
        },
        onUpdate: ({ editor }) => {
            dirty.current = true;
            source.value = editorHtml(editor);
            source.dispatchEvent(new Event("input", { bubbles: true }));
        },
        onBlur: ({ editor }) => {
            if (dirty.current) source.value = editorHtml(editor);
        },
    });

    useEffect(() => {
        props.onEditor(editor);
        return () => props.onEditor(null);
    }, [editor]);

    useEffect(() => {
        if (!editor) return;
        const form = source.closest("form");
        const syncBeforeSubmit = () => {
            if (dirty.current) source.value = editorHtml(editor);
        };
        const resetFromSource = () => {
            window.setTimeout(() => {
                editor.commands.setContent(source.value || "", {
                    emitUpdate: false,
                });
                dirty.current = false;
            });
        };
        const focusEditorForInvalidSource = (event: Event) => {
            event.preventDefault();
            editor.commands.focus("start", { scrollIntoView: false });
        };
        const label = source.id
            ? document.querySelector<HTMLLabelElement>(
                  `label[for="${CSS.escape(source.id)}"]`
              )
            : null;
        const focusFromLabel = (event: Event) => {
            event.preventDefault();
            editor.commands.focus(undefined, { scrollIntoView: false });
        };

        form?.addEventListener("submit", syncBeforeSubmit, true);
        form?.addEventListener("reset", resetFromSource);
        source.addEventListener("invalid", focusEditorForInvalidSource);
        label?.addEventListener("click", focusFromLabel);
        return () => {
            form?.removeEventListener("submit", syncBeforeSubmit, true);
            form?.removeEventListener("reset", resetFromSource);
            source.removeEventListener("invalid", focusEditorForInvalidSource);
            label?.removeEventListener("click", focusFromLabel);
        };
    }, [editor, source]);

    return (
        <div
            className={`collab-editor gw-standalone-editor gw-editor-profile-${props.profile}`}
            data-editor-profile={props.profile}
        >
            <EditorContext.Provider value={{ editor }}>
                <Toolbar editor={editor} history profile={props.profile} />
                <EditorContent editor={editor} />
            </EditorContext.Provider>
        </div>
    );
}

export function mountStandaloneEditor(
    source: HTMLTextAreaElement
): MountedEditor | null {
    if (mountedEditors.has(source)) return mountedEditors.get(source)!;
    if (!source.isConnected) return null;

    const profile = profileFor(source);
    const originalAriaHidden = source.getAttribute("aria-hidden");
    const originalTabIndex = source.getAttribute("tabindex");
    const host = document.createElement("div");
    host.className = "gw-standalone-editor-host";
    host.style.setProperty(
        "--gw-editor-min-height",
        `${minimumHeightFor(source, profile)}px`
    );
    source.insertAdjacentElement("afterend", host);

    const root = createRoot(host);
    const handle: MountedEditor = {
        editor: null,
        host,
        root,
        source,
        destroy: () => undefined,
        syncFromSource: () => undefined,
    };
    const destroy = () => {
        if (!mountedEditors.has(source)) return;
        mountedEditors.delete(source);
        root.unmount();
        host.remove();
        source.classList.remove("gw-tiptap-source");
        if (originalAriaHidden === null) {
            source.removeAttribute("aria-hidden");
        } else {
            source.setAttribute("aria-hidden", originalAriaHidden);
        }
        if (originalTabIndex === null) {
            source.removeAttribute("tabindex");
        } else {
            source.setAttribute("tabindex", originalTabIndex);
        }
    };
    handle.destroy = destroy;
    handle.syncFromSource = () => {
        handle.editor?.commands.setContent(source.value || "", {
            emitUpdate: false,
        });
    };
    mountedEditors.set(source, handle);

    flushSync(() => {
        root.render(
            <StandaloneRichTextEditor
                source={source}
                profile={profile}
                onEditor={(editor) => {
                    handle.editor = editor;
                }}
            />
        );
    });
    source.classList.add("gw-tiptap-source");
    source.setAttribute("aria-hidden", "true");
    source.setAttribute("tabindex", "-1");
    return handle;
}

function textareasWithin(root: ParentNode | Element): HTMLTextAreaElement[] {
    const textareas =
        root instanceof HTMLTextAreaElement
            ? [root]
            : Array.from(
                  root.querySelectorAll<HTMLTextAreaElement>("textarea")
              );
    return textareas;
}

export function initStandaloneEditors(
    root: ParentNode | Element = document,
    options?: InitOptions
): MountedEditor[] {
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;
    const mounted = textareasWithin(root)
        .filter((source) => shouldEnhance(source, options))
        .flatMap((source) => {
            const handle = mountStandaloneEditor(source);
            return handle ? [handle] : [];
        });
    if (options?.preserveScroll && mounted.length) {
        window.requestAnimationFrame(() => window.scrollTo(scrollX, scrollY));
    }
    return mounted;
}

export function destroyStandaloneEditors(
    root: ParentNode | Element = document
) {
    for (const handle of Array.from(mountedEditors.values())) {
        if (
            root === document ||
            (root instanceof Node &&
                (root.contains(handle.source) || root.contains(handle.host)))
        ) {
            handle.destroy();
        }
    }
}

function initializeVisiblePane(target: EventTarget | null) {
    if (target instanceof Element) initStandaloneEditors(target);
}

function observeDynamicEditors() {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const removedNode of Array.from(mutation.removedNodes)) {
                if (removedNode instanceof Element) {
                    destroyStandaloneEditors(removedNode);
                }
            }
            for (const addedNode of Array.from(mutation.addedNodes)) {
                if (addedNode instanceof Element) {
                    initStandaloneEditors(addedNode);
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

declare global {
    interface Window {
        gwDestroyTiptapEditors: typeof destroyStandaloneEditors;
        gwInitTiptapStableContainer: (
            root: ParentNode | Element
        ) => MountedEditor[];
        gwInitTiptapTextareas: typeof initStandaloneEditors;
        gwRequestFormSubmit: typeof requestFormSubmit;
        gwSyncTiptapFromTextarea: (source: HTMLTextAreaElement) => void;
    }
}

window.gwDestroyTiptapEditors = destroyStandaloneEditors;
window.gwInitTiptapTextareas = initStandaloneEditors;
window.gwInitTiptapStableContainer = (root) =>
    initStandaloneEditors(root, {
        includeInactiveTabs: true,
        preserveScroll: true,
    });
window.gwRequestFormSubmit = requestFormSubmit;
window.gwSyncTiptapFromTextarea = (source) =>
    mountedEditors.get(source)?.syncFromSource();

document.addEventListener("shown.bs.tab", (event) => {
    const trigger = event.target;
    const selector =
        trigger instanceof HTMLElement
            ? trigger.getAttribute("data-bs-target") ||
              trigger.getAttribute("href")
            : null;
    if (selector?.startsWith("#")) {
        initializeVisiblePane(document.querySelector(selector));
    }
});
document.addEventListener("shown.bs.modal", (event) =>
    initializeVisiblePane(event.target)
);
document.addEventListener(
    "toggle",
    (event) => {
        if (event.target instanceof HTMLDetailsElement && event.target.open) {
            initStandaloneEditors(event.target);
        }
    },
    true
);

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        () => {
            initStandaloneEditors();
            observeDynamicEditors();
        },
        { once: true }
    );
} else {
    initStandaloneEditors();
    observeDynamicEditors();
}
