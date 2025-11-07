// Makes an HTMLElement for TipTap, either using the document on browser or zeed-dom on node.
let mkElem: (name: string) => HTMLElement;
if (import.meta.env.SSR) {
    mkElem = (await import("zeed-dom")).h;
} else {
    mkElem = (name) => document.createElement(name);
}

export default mkElem;
