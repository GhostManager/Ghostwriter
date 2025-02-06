import { getSchema } from "@tiptap/core";
import { type Extensions } from "@tiptap/core";
import EXTENSIONS_front from "../../frontend/src/collab_forms/tiptap_extensions";

const EXTENSIONS: Extensions = EXTENSIONS_front as Extensions;
export default EXTENSIONS;

export const SCHEMA = getSchema(EXTENSIONS);
