// The regular mark extensions but also parses `<span class="bold/italic/underline/highlight">` for
// tinymce compatibility

import Bold from "@tiptap/extension-bold";
import Italic from "@tiptap/extension-italic";
import Underline from "@tiptap/extension-underline";
import Highlight from "@tiptap/extension-highlight";
import mkElem from "./mkelem";

// TinyMCE uses one span with multiple classes to represent combined bold/italic/underline/etc., but
// Tiptap assumes one element per mark. So fake it with this `contentElement` function that strips
// the class off and resubmits the span.
function unwrapClass(node: Node, cls: string): HTMLElement {
    const n = node as HTMLElement;
    n.classList.remove(cls);
    if (n.classList.length === 0) {
        return n;
    }
    const wrapper = mkElem("div");
    wrapper.appendChild(node.cloneNode(true));
    return wrapper;
}

export const BoldCompat = Bold.extend({
    parseHTML() {
        const arr = Array.from(Bold.config.parseHTML!.call(this)!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("bold") && null,
            contentElement: (node) => unwrapClass(node, "bold"),
        });
        return arr;
    },
});

export const ItalicCompat = Italic.extend({
    parseHTML() {
        const arr = Array.from(Italic.config.parseHTML!.call(this)!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("italic") && null,
            contentElement: (node) => unwrapClass(node, "italic"),
        });
        return arr;
    },
});

export const UnderlineCompat = Underline.extend({
    parseHTML() {
        const arr = Array.from(Underline.config.parseHTML!.call(this)!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("underline") && null,
            contentElement: (node) => unwrapClass(node, "underline"),
        });
        return arr;
    },
});

export const HighlightCompat = Highlight.extend({
    parseHTML() {
        const arr = Array.from(Highlight.config.parseHTML!.call(this)!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("highlight") && null,
            contentElement: (node) => unwrapClass(node, "highlight"),
        });
        return arr;
    },
});
