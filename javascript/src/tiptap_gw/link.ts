import TTLink from "@tiptap/extension-link";

const Link = TTLink.extend({
    addPasteRules() {
        return [];
    },
});
export default Link;
