// Collab extensions aren't included here since they require runtime configuration. They don't
// change the schema.

import StarterKit from "@tiptap/starter-kit";
import Subscript from "@tiptap/extension-subscript";
import Superscript from "@tiptap/extension-superscript";
import { type Extensions } from "@tiptap/core";

import PageBreak from "./pagebreak";
import Evidence from "./evidence";
import FormattedCodeblock from "./codeblock";
import {
    BoldCompat,
    CodeCompat,
    HighlightCompat,
    ItalicCompat,
    UnderlineCompat,
} from "./bold_italic_underline";
import {
    TableWithCaption,
    TableCaption,
    GwTable,
    GwTableCell,
    GwTableHeader,
    GwTableRow,
} from "./table";
import { HeadingWithId } from "./heading";
import Color from "./color";
import CaseChange from "./case_change";
import Link from "./link";
import Image from "./image";
import TextAlign from "./text_align";
import Caption from "./caption";
import Footnote from "./footnote";
import { PassiveVoiceDecoration } from "./passive_voice_decoration";
import DateTimeShortcuts from "./now_shortcut";
import { LegacyTextStyleCompat } from "./legacy_html";

export function createGhostwriterExtensions(options?: {
    undoRedo?: boolean;
}): Extensions {
    return [
        StarterKit.configure({
            undoRedo: options?.undoRedo ? {} : false,
            heading: false,
            codeBlock: false,
            link: false,
            underline: false,
            bold: false,
            italic: false,
            code: false,
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
            types: [
                "gwheading",
                "paragraph",
                "bulletList",
                "orderedList",
                "table",
                "tableCell",
                "tableHeader",
            ],
        }),
        CodeCompat,
        HighlightCompat,
        LegacyTextStyleCompat,
        GwTable,
        GwTableRow,
        GwTableHeader,
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
        Caption,
        Footnote,
        PassiveVoiceDecoration,
        DateTimeShortcuts,
    ];
}

const EXTENSIONS = createGhostwriterExtensions();
export default EXTENSIONS;
