import * as Y from "yjs";
import {
    prosemirrorToYXmlFragment,
    yXmlFragmentToProseMirrorRootNode,
} from "y-prosemirror";
import { createHTMLDocument, parseHTML, VHTMLDocument } from "zeed-dom";
import { DOMParser, DOMSerializer } from "@tiptap/pm/model";

import { SCHEMA } from "./tiptap_extensions";

/**
 * Parses rich text HTML and inserts the content to the YJS XmlFragment
 * @param html Source HTML to read
 * @param frag Empty XmlFragment to write to
 */
export function htmlToYjs(html: string, frag: Y.XmlFragment) {
    // Partially copied from `@tiptap/html` `generateJSON`, but using the constant SCHEMA
    // and not converting to JSON just to read it again.
    const dom = parseHTML(html) as any;
    const node = DOMParser.fromSchema(SCHEMA).parse(dom);

    prosemirrorToYXmlFragment(node, frag);
}

/**
 * Gets a rich text HTML string from a YJS XmlFragment
 * @param frag Fragment to read
 * @returns The HTML source
 */
export function yjsToHtml(frag: Y.XmlFragment): string {
    const node = yXmlFragmentToProseMirrorRootNode(frag, SCHEMA);

    // Partially copied from `@tiptap/html` `getHTMLFromFragment`
    const doc = DOMSerializer.fromSchema(SCHEMA).serializeFragment(
        node.content,
        {
            document: createHTMLDocument() as any,
        }
    ) as unknown as VHTMLDocument;

    return doc.render();
}

/**
 * Inserts tags into a YJS Map
 * @param tags Tags to insert
 * @param map Map to insert into
 */
export function tagsToYjs(tags: string[], map: Y.Map<boolean>) {
    for (const tag of tags) {
        map.set(tag, true);
    }
}

/**
 * Gets an array of tags from a YJS map
 * @param map Map to get tags from
 * @returns Array of tags, in arbitrary order
 */
export function yjsToTags(map: Y.Map<boolean>): string[] {
    let tags = [];
    for (const [key, value] of map.entries()) {
        if (value) tags.push(key);
    }
    return tags;
}
