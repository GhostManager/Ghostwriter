// Collab extensions aren't included here since they require runtime configuration. They don't
// change the schema.

import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import { Table, TableHeader, TableRow } from "@tiptap/extension-table";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import { type Extensions } from "@tiptap/core";

import PageBreak from "./pagebreak";
import Evidence from "./evidence";
import FormattedCodeblock from "./codeblock";
import {
    BoldCompat,
    HighlightCompat,
    ItalicCompat,
    UnderlineCompat,
} from "./bold_italic_underline";
import { TableWithCaption, TableCaption, GwTableCell } from "./table";
import { HeadingWithId } from "./heading";
import Color from "./color";
import CaseChange from "./case_change";
import Link from "./link";
import Image from "./image";

const EXTENSIONS: Extensions = [
    StarterKit.configure({
        undoRedo: false,
        heading: false,
        codeBlock: false,
        link: false,
        underline: false,
        bold: false,
        italic: false,
        horizontalRule: false,
    }),
    HeadingWithId,
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
        autolink: false,
        linkOnPaste: false,
        shouldAutoLink: () => false,
    }),
    TextAlign.configure({
        types: ["heading", "paragraph"],
    }),
    HighlightCompat,
    Table,
    TableRow,
    TableHeader,
    GwTableCell,
    PageBreak,
    Subscript,
    Superscript,
    Evidence,
    TableWithCaption,
    TableCaption,
    Color,
    Image,
    CaseChange,
];

export default EXTENSIONS;
