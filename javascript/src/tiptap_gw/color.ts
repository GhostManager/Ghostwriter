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
                    console.log(
                        "DEBUG",
                        node.hasAttribute("data-color"),
                        node.style.color
                    );
                    if (node.hasAttribute("data-color")) return null;
                    const color = node.style.color;
                    if (color !== "") return null;
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
