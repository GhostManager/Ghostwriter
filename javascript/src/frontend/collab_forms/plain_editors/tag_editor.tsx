/// Tag editor.

import * as Y from "yjs";
import Tagify from "@yaireo/tagify";
import { useEffect, useMemo, useRef } from "react";
import { HocuspocusProvider } from "@hocuspocus/provider";
import { FocusedUsersList, setFocusStyles, useYMapFocus } from "./focus";

export function TagEditor(props: {
    connected: boolean;
    provider: HocuspocusProvider;
    docKey: string;
    id?: string;
    className?: string;
}) {
    const map = useMemo(
        () => props.provider.document.get(props.docKey, Y.Map<boolean>),
        [props.provider, props.docKey]
    );

    const { focusedUsers, onFocus, onBlur } = useYMapFocus(
        props.provider.awareness!,
        map,
        ""
    );

    const inputRef = useRef<HTMLInputElement>(null);
    const taggify = useRef<Tagify | null>(null);
    useEffect(() => {
        taggify.current = new Tagify(inputRef.current!, {
            createInvalidTags: false,
            skipInvalid: true,
            classNames: {
                namespace: "tagify form-control",
            },
            placeholder: "ATT&CK:T1555, privesc, ...",
        });

        taggify.current.addTags(Array.from(map.keys()));

        map.observe((ev, _tx) => {
            for (const key of ev.keysChanged) {
                if (map.has(key) && !taggify.current?.isTagDuplicate(key))
                    taggify.current?.addTags([key]);
                else if (!map.has(key) && taggify.current?.isTagDuplicate(key))
                    taggify.current?.removeTags([key], true);
            }
        });

        taggify.current.on("add", (ev) => {
            //console.log("add", ev.detail);
            const tag = ev.detail.data!.value;
            if (!map.get(tag)) {
                // Don't re-add tags - doing so causes redundant updates and history entries.
                map.set(tag, true);
            }
        });
        taggify.current.on("remove", (ev) => {
            //console.log("remove", ev.detail);
            map.delete(ev.detail.data!.value);
        });
        taggify.current.on("edit:updated", (ev) => {
            //console.log("edit:updated", ev.detail);
            const oldTag = (ev.detail as any).previousData.value as string; // types broken
            const newTag = ev.detail.data!.tag.value;
            if (oldTag === newTag) return;
            map.delete(oldTag);
            map.set(newTag, true);
        });
        taggify.current.on("focus", onFocus);
        taggify.current.on("blur", onBlur);

        return () => {
            taggify.current?.destroy();
        };
    }, [map]);

    const style = setFocusStyles(focusedUsers);
    useEffect(() => {
        taggify.current!.DOM.scope.style.setProperty(
            "outline",
            (style.outline ?? "") as string
        );
    }, [style.outline]);

    useEffect(() => {
        if (taggify.current) taggify.current.setDisabled(!props.connected);
    }, [props.connected]);

    return (
        <>
            <input id={props.id} type="text" ref={inputRef} />
            <FocusedUsersList focusedUsers={focusedUsers} />
        </>
    );
}
