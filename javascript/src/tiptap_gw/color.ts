import { Mark } from "@tiptap/core";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        color: {
            setColor: (attributes: { color: string }) => ReturnType;
            unsetColor: () => ReturnType;
        };
    }
}

const SAFE_HEX_COLOR_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
const DEFAULT_COLOR = "#f00";

function sanitizeColor(color: unknown): string {
    if (typeof color === "string" && SAFE_HEX_COLOR_RE.test(color)) {
        return color;
    }
    return DEFAULT_COLOR;
}

function rgbToHex(rgb: string): string | null {
    const match = rgb.match(
        /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/,
    );
    if (!match) return null;
    const [, r, g, b] = match;
    return (
        "#" +
        [r, g, b]
            .map((c) => parseInt(c, 10).toString(16).padStart(2, "0"))
            .join("")
    );
}

const ColorMark = Mark.create({
    name: "color",

    addAttributes() {
        return {
            color: {
                default: DEFAULT_COLOR,
                parseHTML: (element) => {
                    const raw =
                        element.getAttribute("data-color") ||
                        element.style.color;
                    return sanitizeColor(raw) !== DEFAULT_COLOR
                        ? sanitizeColor(raw)
                        : sanitizeColor(rgbToHex(raw || ""));
                },
                renderHTML: (attributes) => {
                    const color = sanitizeColor(attributes.color);
                    return {
                        "data-color": color,
                        style: `color: ${color};`,
                    };
                },
            },
        };
    },
    parseHTML() {
        return [
            {
                tag: "span",
                getAttrs: (node) => {
                    if (node.hasAttribute("data-color")) {
                        // Has data-color from this mark, apply
                        return null;
                    }
                    const color = node.style.color;
                    if (color !== undefined && color !== "") {
                        // Has a color style from tinymce, apply
                        return null;
                    }

                    // Has neither, don't apply
                    return false;
                },
            },
        ];
    },
    renderHTML({ HTMLAttributes }) {
        return ["span", HTMLAttributes, 0];
    },
    addCommands() {
        return {
            setColor:
                ({ color }) =>
                ({ commands }) => {
                    return commands.setMark(this.name, {
                        color: sanitizeColor(color),
                    });
                },
            unsetColor:
                () =>
                ({ commands }) => {
                    return commands.unsetMark(this.name);
                },
        };
    },
});
export default ColorMark;
