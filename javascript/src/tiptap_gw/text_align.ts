// Extension of tiptap's builtin alignment extension that also picks up TinyMCE's alignment classes

import TTTextAlign from "@tiptap/extension-text-align";

const TextAlign = TTTextAlign.extend({
    addGlobalAttributes() {
        const attrs = TTTextAlign.config.addGlobalAttributes!.call(this);
        attrs[0].attributes.textAlign!.parseHTML = (el) => {
            let align = el.style.textAlign;
            if (align !== "" && !this.options.alignments.includes(align))
                align = "";

            // If no tiptap-specified alignment, check TinyMCE classes.
            if (align === "") {
                for (const cls of this.options.alignments) {
                    if (el.classList.contains(cls)) {
                        align = cls;
                        break;
                    }
                }
            }
            return align === "" ? this.options.defaultAlignment : align;
        };
        return attrs;
    },
});
export default TextAlign;
