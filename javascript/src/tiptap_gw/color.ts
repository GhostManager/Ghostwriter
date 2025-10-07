import { Mark } from "@tiptap/core";

declare module "@tiptap/core" {
    interface Commands<ReturnType> {
        color: {
            setColor: (attributes: { color: string }) => ReturnType;
            unsetColor: () => ReturnType;
        };
    }
}

const ColorMark = Mark.create({
    name: "color",

    addAttributes() {
        return {
            color: {
                default: "#f00",
                parseHTML: (element) =>
                    element.getAttribute("data-color") || element.style.color,
                renderHTML: (attributes) => {
                    return {
                        "data-color": attributes.color,
                        style: `color: ${attributes.color};`,
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
                    return commands.setMark(this.name, { color });
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
