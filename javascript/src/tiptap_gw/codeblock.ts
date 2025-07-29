// Same as CodeBlock but accepts marks inside of it.

import { DOMNode } from "@tiptap/core";
import CodeBlock from "@tiptap/extension-code-block";

const FormattedCodeblock = CodeBlock.extend({
    marks: "_",

    // CodeBlock emits a <pre> and <code> but only parses the <pre>, so with marks, tiptap will think
    // everything is wrapped in an inline code mark. Alter the parser to unwrap the code element.
    parseHTML() {
        return [
            {
                tag: "pre",
                preserveWhitespace: "full",
                contentElement: (el: DOMNode) =>
                    el.childNodes.length == 1 &&
                    el.childNodes[0].nodeName === "CODE"
                        ? (el.childNodes[0] as HTMLElement)
                        : (el as HTMLElement),
            },
        ];
    },
});

export default FormattedCodeblock;
