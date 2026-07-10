import TTLink from "@tiptap/extension-link";

const ALLOWED_LINK_PROTOCOLS = new Set(["http", "https", "mailto", "tel"]);
const DISALLOWED_LINK_CHARS = /[\u0000-\u0020\u007f]/;

export function sanitizeLinkHref(href: string): string | null {
    const trimmedHref = href.trim();
    if (!trimmedHref || DISALLOWED_LINK_CHARS.test(trimmedHref)) {
        return null;
    }
    if (trimmedHref.startsWith("#") || trimmedHref.startsWith("?")) {
        return trimmedHref;
    }
    if (
        (trimmedHref.startsWith("/") && !trimmedHref.startsWith("//")) ||
        trimmedHref.startsWith("./") ||
        trimmedHref.startsWith("../")
    ) {
        return trimmedHref;
    }

    const schemeMatch = trimmedHref.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):/);
    if (schemeMatch) {
        return ALLOWED_LINK_PROTOCOLS.has(schemeMatch[1].toLowerCase())
            ? trimmedHref
            : null;
    }
    if (trimmedHref.startsWith("//")) {
        return null;
    }
    return trimmedHref;
}

const Link = TTLink.extend({
    // Disable paste rules to prevent auto-linking when pasting URLs
    addPasteRules() {
        return [];
    },
});
export default Link;
