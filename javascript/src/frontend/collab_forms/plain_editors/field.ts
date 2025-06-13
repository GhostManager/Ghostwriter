/** Last-write-wins editors. They will sync but don't have doc-style collaborative editing - the latest update will overwrite the others. */

import * as Y from "yjs";
import { useEffect, useMemo, useReducer, useRef } from "react";

/**
 * Gets and observes a YJS map key.
 * @param map The YJS map to observe
 * @param key The key of the YJS map to get and observe
 * @param defaultValue The value to return if the key is missing
 * @returns The current value and a setter that sets the value on the YJS map.
 */
export function usePlainField<T>(
    map: Y.Map<T>,
    key: string,
    defaultValue: T,
    onExternalChange?: (value: T) => void
): [T, (v: T) => void] {
    const forceUpdate = useReducer((x) => x + 1, 0)[1];

    const onExternalChangeRef = useRef(onExternalChange);
    onExternalChangeRef.current = onExternalChange;

    useEffect(() => {
        const cbObserve = (ev: Y.YMapEvent<T>) => {
            if (ev.keysChanged.has(key)) {
                if (onExternalChangeRef.current)
                    onExternalChangeRef.current(map.get(key) ?? defaultValue);
                forceUpdate();
            }
        };
        map.observe(cbObserve);
        return () => {
            map.unobserve(cbObserve);
        };
    }, [map, key, defaultValue]);

    const setInDoc = useMemo(
        () => (v: T) => {
            if (v === null) map.delete(key);
            else map.set(key, v);
            forceUpdate();
        },
        [map, key]
    );

    const value = map.get(key) ?? defaultValue;

    return [value, setInDoc];
}
