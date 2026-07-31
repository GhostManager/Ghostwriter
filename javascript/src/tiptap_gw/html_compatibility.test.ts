import assert from "node:assert/strict";

import type { JSONContent } from "@tiptap/core";
import { generateHTML, generateJSON } from "@tiptap/html/server";

import { createGhostwriterExtensions } from ".";

function walk(node: JSONContent): JSONContent[] {
    return [node, ...(node.content || []).flatMap(walk)];
}

const extensions = createGhostwriterExtensions({ undoRedo: true });
const legacyHtml = `
    <h2 id="access-path">Access path</h2>
    <p class="right">
        <span class="bold italic underline">Operator note</span>
        <span style="color: #50b071; font-family: Arial, sans-serif; font-size: 14pt">preserved formatting</span>
    </p>
    <p class="full">
        <del>retired</del> <sub>sub</sub> <sup>sup</sup>
        <span class="code">inline code</span>
        <span class="highlight" style="background-color: yellow">highlight</span>
        AT&amp;T&nbsp;operator
    </p>
    <blockquote class="blockquote">Keep this context visible.</blockquote>
    <ul><li>Parent<ul><li>Nested task</li></ul></li></ul>
    <ol><li>First</li><li>Second</li></ol>
    <pre class="rich-code"><code>whoami /all</code></pre>
    <p><a href="https://example.test/path?q=1">Safe link</a></p>
    <hr>
    <div class="page-break"></div>
    <table class="table table-sm table-striped table-bordered right"
           style="border-collapse: collapse; width: 85%; border-style: solid; border-width: 1px">
        <caption>Observed systems</caption>
        <thead><tr class="tablerow1"><th style="background-color: #d3d3d3">Host</th><th>Role</th></tr></thead>
        <tbody><tr><td colspan="2">dc01.example.test</td></tr></tbody>
    </table>
    <div class="richtext-evidence" data-evidence-id="42"></div>
    <div data-gw-image="CLIENT_LOGO"></div>
`;

const json = generateJSON(legacyHtml, extensions);
const nodes = walk(json);
const output = generateHTML(json, extensions);

assert.equal(
    nodes.find((node) => node.type === "gwheading")?.attrs?.bookmark,
    "access-path"
);
assert.equal(
    nodes.find((node) => node.type === "paragraph")?.attrs?.textAlign,
    "right"
);
assert.ok(
    nodes.some(
        (node) =>
            node.type === "paragraph" && node.attrs?.textAlign === "justify"
    )
);

const operatorNote = nodes.find((node) => node.text === "Operator note");
assert.deepEqual(
    new Set((operatorNote?.marks || []).map((mark) => mark.type)),
    new Set(["bold", "italic", "underline"])
);

const legacyStyle = nodes.find((node) => node.text === "preserved formatting");
assert.ok(
    legacyStyle?.marks?.some(
        (mark) =>
            mark.type === "legacyTextStyle" && mark.attrs?.fontSize === "14pt"
    )
);
assert.ok(
    legacyStyle?.marks?.some(
        (mark) =>
            mark.type === "color" ||
            (mark.type === "legacyTextStyle" && mark.attrs?.color === "#50b071")
    )
);

for (const [text, mark] of [
    ["retired", "strike"],
    ["sub", "subscript"],
    ["sup", "superscript"],
    ["inline code", "code"],
    ["highlight", "highlight"],
]) {
    assert.ok(
        nodes
            .find((node) => node.text === text)
            ?.marks?.some((candidate) => candidate.type === mark),
        `Expected ${mark} to survive legacy HTML parsing`
    );
}
assert.ok(nodes.some((node) => node.text?.includes("AT&T\u00a0operator")));

for (const requiredType of [
    "blockquote",
    "bulletList",
    "orderedList",
    "codeBlock",
    "horizontalRule",
    "pageBreak",
    "tableWithCaption",
    "evidence",
    "gwImage",
]) {
    assert.ok(
        nodes.some((node) => node.type === requiredType),
        `Expected ${requiredType} to survive legacy HTML parsing`
    );
}

assert.equal(nodes.find((node) => node.type === "evidence")?.attrs?.id, "42");
assert.equal(
    nodes.find((node) => node.type === "gwImage")?.attrs?.imgName,
    "CLIENT_LOGO"
);
assert.equal(
    nodes.find((node) => node.type === "table")?.attrs?.style,
    "border-collapse: collapse; width: 85%; border-style: solid; border-width: 1px"
);
assert.ok(
    nodes.some(
        (node) =>
            node.type === "tableHeader" &&
            ["#d3d3d3", "rgb(211, 211, 211)"].includes(
                String(node.attrs?.bgColor)
            )
    )
);

assert.match(output, /data-bookmark="access-path"/);
assert.match(output, /font-family: Arial, sans-serif/);
assert.match(output, /font-size: 14pt/);
assert.match(output, /data-evidence-id="42"/);
assert.match(output, /data-gw-image="CLIENT_LOGO"/);
assert.doesNotMatch(output, /<img\b/i);

const unsafeLinkJson = generateJSON(
    '<p><a href="javascript:alert(1)">unsafe</a></p>',
    extensions
);
const unsafeOutput = generateHTML(unsafeLinkJson, extensions);
assert.doesNotMatch(unsafeOutput, /javascript:/i);

console.log("Ghostwriter legacy HTML compatibility checks passed.");
