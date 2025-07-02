// Header that adds an ID attribute for bookmarks

import { type Attributes } from "@tiptap/core";
import Heading from "@tiptap/extension-heading";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        gwheading: Commands<ReturnType>["heading"] & {
            setHeadingBookmark: (name: string | undefined) => ReturnType;
        };
    }
}

export const HeadingWithId = Heading.extend({
    name: "gwheading",

    addAttributes() {
        const attrs = Heading.config.addAttributes!.call(this) as Attributes;
        attrs.bookmark = {
            default: undefined,
            parseHTML: (el) =>
                el.getAttribute("data-bookmark") || el.getAttribute("id"),
            renderHTML: (attr) => ({ "data-bookmark": attr.bookmark }),
        };
        return attrs;
    },

    addCommands() {
        const cmds = Heading.config.addCommands!.call(this);
        cmds.setHeadingBookmark =
            (name) =>
            ({ commands, can }) => {
                // Check if we're even in a heading, and don't enable this command if so.
                if (!can().deleteNode(this.name)) return false;
                return commands.updateAttributes(this.name, { bookmark: name });
            };
        return cmds;
    },
});
