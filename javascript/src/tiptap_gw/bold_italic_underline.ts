// The regular mark extensions but also parses `<span class="bold/italic/underline/highlight">` for
// tinymce compatibility

import Bold from "@tiptap/extension-bold";
import Italic from "@tiptap/extension-italic";
import Underline from "@tiptap/extension-underline";
import Highlight from "@tiptap/extension-highlight";

export const BoldCompat = Bold.extend({
    parseHTML() {
        const arr = Array.from(Bold.config.parseHTML!.bind(this)()!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("bold") && null,
        });
        return arr;
    },
});

export const ItalicCompat = Italic.extend({
    parseHTML() {
        const arr = Array.from(Italic.config.parseHTML!.bind(this)()!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("italic") && null,
        });
        return arr;
    },
});

export const UnderlineCompat = Underline.extend({
    parseHTML() {
        const arr = Array.from(Underline.config.parseHTML!.bind(this)()!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("underline") && null,
        });
        return arr;
    },
});

export const HighlightCompat = Highlight.extend({
    parseHTML() {
        const arr = Array.from(Highlight.config.parseHTML!.bind(this)()!);
        arr.push({
            tag: "span",
            getAttrs: (node) => node.classList.contains("highlight") && null,
        });
        return arr;
    },
});
