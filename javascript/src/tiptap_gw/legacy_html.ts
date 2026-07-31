import { Mark } from "@tiptap/core";

import { rgbToHex } from "./color";

const SAFE_FONT_SIZE =
    /^(?:xx-small|x-small|small|medium|large|x-large|xx-large|\d+(?:\.\d+)?(?:px|pt|em|rem|%))$/i;
const SAFE_FONT_FAMILY = /^[A-Za-z0-9 ,"'\-]+$/;
const SAFE_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i;

function sanitizeFontSize(value: unknown): string | undefined {
    if (typeof value !== "string") return undefined;
    const trimmed = value.trim();
    return SAFE_FONT_SIZE.test(trimmed) ? trimmed : undefined;
}

function sanitizeFontFamily(value: unknown): string | undefined {
    if (typeof value !== "string") return undefined;
    const trimmed = value.trim();
    return SAFE_FONT_FAMILY.test(trimmed) ? trimmed : undefined;
}

function sanitizeColor(value: unknown): string | undefined {
    if (typeof value !== "string") return undefined;
    const trimmed = value.trim();
    if (SAFE_COLOR.test(trimmed)) return trimmed;
    return rgbToHex(trimmed) || undefined;
}

/**
 * Retain the font family and size spans TinyMCE allowed through its Format
 * menu. New Ghostwriter UI does not promote these controls, but opening and
 * saving an existing field must not discard them.
 */
export const LegacyTextStyleCompat = Mark.create({
    name: "legacyTextStyle",

    addAttributes() {
        return {
            fontFamily: {
                default: undefined,
                parseHTML: (element) =>
                    sanitizeFontFamily(element.style.fontFamily),
            },
            fontSize: {
                default: undefined,
                parseHTML: (element) =>
                    sanitizeFontSize(element.style.fontSize),
            },
            color: {
                default: undefined,
                parseHTML: (element) => sanitizeColor(element.style.color),
            },
        };
    },

    parseHTML() {
        return [
            {
                tag: "span[style]",
                getAttrs: (element) => {
                    const fontFamily = sanitizeFontFamily(
                        element.style.fontFamily
                    );
                    const fontSize = sanitizeFontSize(element.style.fontSize);
                    const color = sanitizeColor(element.style.color);
                    return fontFamily || fontSize || color
                        ? { fontFamily, fontSize, color }
                        : false;
                },
            },
            {
                tag: "font[face], font[size]",
                getAttrs: (element) => {
                    const fontFamily = sanitizeFontFamily(
                        element.getAttribute("face")
                    );
                    const legacySize = element.getAttribute("size");
                    const legacySizes: Record<string, string> = {
                        "1": "xx-small",
                        "2": "x-small",
                        "3": "small",
                        "4": "medium",
                        "5": "large",
                        "6": "x-large",
                        "7": "xx-large",
                    };
                    const fontSize = legacySize
                        ? legacySizes[legacySize]
                        : undefined;
                    return fontFamily || fontSize
                        ? { fontFamily, fontSize }
                        : false;
                },
            },
        ];
    },

    renderHTML({ HTMLAttributes }) {
        const fontFamily = sanitizeFontFamily(HTMLAttributes.fontFamily);
        const fontSize = sanitizeFontSize(HTMLAttributes.fontSize);
        const color = sanitizeColor(HTMLAttributes.color);
        const declarations = [
            fontFamily ? `font-family: ${fontFamily}` : "",
            fontSize ? `font-size: ${fontSize}` : "",
            color ? `color: ${color}` : "",
        ].filter(Boolean);
        return [
            "span",
            declarations.length ? { style: declarations.join("; ") } : {},
            0,
        ];
    },
});
