import TTLink from "@tiptap/extension-link";

const Link = TTLink.extend({
    // Disable paste rules to prevent auto-linking when pasting URLs
    addPasteRules() {
        return [];
    },
});
export default Link;
