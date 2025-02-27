import * as Y from "yjs";

/*
export function getByPath<T>(doc: Y.Doc, path: string | (string | number)[], top_level_type: any): T {
    const arrPath = typeof path === "string" ? [path] : path;
    const rootPath = arrPath[0];
    if (typeof rootPath === "number")
        throw new Error("Root path must be a string");

    if (arrPath.length === 1) {
        return doc.get(rootPath, top_level_type);
    }


}
*/
