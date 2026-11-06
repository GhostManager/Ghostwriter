function hasRichTextCandidate(root: ParentNode = document): boolean {
    return Array.from(
        root.querySelectorAll<HTMLTextAreaElement>("textarea")
    ).some(
        (source) =>
            !source.disabled &&
            !source.classList.contains("empty-form") &&
            !source.classList.contains("no-auto-tiptap") &&
            !source.classList.contains("no-auto-rich-text") &&
            !source.closest(".empty-form, [id^='empty-form-']")
    );
}

let editorRuntime: Promise<unknown> | null = null;

function loadEditorRuntime() {
    if (!editorRuntime) {
        editorRuntime = import("./standalone_tiptap");
    }
    return editorRuntime;
}

function startEditorLoader() {
    if (hasRichTextCandidate()) {
        void loadEditorRuntime();
        return;
    }

    const observer = new MutationObserver((mutations) => {
        const addedCandidate = mutations.some((mutation) =>
            Array.from(mutation.addedNodes).some(
                (node) =>
                    (node instanceof HTMLTextAreaElement &&
                        hasRichTextCandidate(node.parentElement || document)) ||
                    (node instanceof Element && hasRichTextCandidate(node))
            )
        );
        if (addedCandidate) {
            observer.disconnect();
            void loadEditorRuntime();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startEditorLoader, {
        once: true,
    });
} else {
    startEditorLoader();
}
