// Collab extensions aren't included here since they require runtime configuration. They don't
// change the schema.

import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Link from "@tiptap/extension-link";
import TextAlign from "@tiptap/extension-text-align";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import Highlight from "@tiptap/extension-highlight";
import { type Extensions } from "@tiptap/core";

import PageBreak from "./pagebreak";
import Evidence from "./evidence";
import FormattedCodeblock from "./codeblock";
import {
    BoldCompat,
    ItalicCompat,
    UnderlineCompat,
} from "./bold_italic_underline";

const EXTENSIONS: Extensions = [
    StarterKit.configure({
        history: false,
        codeBlock: false,
        bold: false,
        italic: false,
    }),
    BoldCompat,
    ItalicCompat,
    UnderlineCompat,
    FormattedCodeblock.configure({
        HTMLAttributes: {
            spellcheck: "false",
        },
    }),
    Link.configure({
        openOnClick: false,
    }),
    TextAlign.configure({
        types: ["heading", "paragraph"],
    }),
    Highlight.configure(),
    Table,
    TableRow,
    TableHeader,
    TableCell,
    PageBreak,
    Subscript,
    Superscript,
    Evidence,
];

export default EXTENSIONS;
