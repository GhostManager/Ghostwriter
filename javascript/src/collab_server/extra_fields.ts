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
        } else if (
            spec.type === "checkbox" ||
            spec.type === "single_line_text" ||
            spec.type === "integer" ||
            spec.type === "float" ||
            spec.type === "json"
        ) {
            extra_fields.set(spec.internalName, json[spec.internalName]);
        } else {
            throw new Error("Unrecognized extra field type: " + spec.type);
        }
    }
}

export function extraFieldsFromYdoc(doc: Y.Doc): Record<string, any> {
    const extra_fields = doc.get("extra_fields", Y.Map);
    const out: Record<string, any> = {};
    for (const [key, value] of extra_fields.entries()) {
        if (value instanceof Y.XmlFragment) {
            out[key] = yjsToHtml(value);
        } else {
            out[key] = value;
        }
    }
    return out;
}
