import * as Y from "yjs";
import { htmlToYjs, yjsToHtml } from "./yjs_converters";

export function extraFieldsToYdoc(
    specs: { internalName: string; type: string }[],
    doc: Y.Doc,
    json: Record<string, any>
) {
    const extra_fields = doc.get("extra_fields", Y.Map);
    for (const spec of specs) {
        if (spec.type === "rich_text") {
            const frag = new Y.XmlFragment();
            extra_fields.set(spec.internalName, frag);
            htmlToYjs((json[spec.internalName] ?? "").toString(), frag);
        } else if (spec.type === "json") {
            const subjson = JSON.stringify(json[spec.internalName] ?? null);
            extra_fields.set(spec.internalName, subjson);
        } else if (
            spec.type === "checkbox" ||
            spec.type === "single_line_text" ||
            spec.type === "integer" ||
            spec.type === "float"
        ) {
            extra_fields.set(spec.internalName, json[spec.internalName]);
        } else {
            throw new Error("Unrecognized extra field type: " + spec.type);
        }
    }
}

export function extraFieldsFromYdoc(
    specs: { internalName: string; type: string }[],
    doc: Y.Doc
): Record<string, any> {
    const extra_fields = doc.get("extra_fields", Y.Map);
    const out: Record<string, any> = {};

    for (const spec of specs) {
        if (spec.type === "rich_text") {
            out[spec.internalName] = yjsToHtml(
                extra_fields.get(spec.internalName) as Y.XmlFragment
            );
        } else if (spec.type === "json") {
            let value = extra_fields.get(spec.internalName) as
                | string
                | undefined;
            out[spec.internalName] = JSON.parse(value ?? "undefined");
        } else if (
            spec.type === "checkbox" ||
            spec.type === "single_line_text" ||
            spec.type === "integer" ||
            spec.type === "float"
        ) {
            out[spec.internalName] = extra_fields.get(spec.internalName) as any;
        } else {
            throw new Error("Unrecognized extra field type: " + spec.type);
        }
    }
    return out;
}
