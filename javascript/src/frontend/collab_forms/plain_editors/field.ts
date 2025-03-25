/** Last-write-wins editors. They will sync but don't have doc-style collaborative editing - the latest update will overwrite the others. */

import * as Y from "yjs";
import { useEffect, useMemo, useReducer } from "react";

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
    defaultValue: T
): [T, (v: T) => void] {
    const forceUpdate = useReducer((x) => x + 1, 0)[1];

    useEffect(() => {
        const cbObserve = (ev: Y.YMapEvent<T>) => {
            if (ev.keysChanged.has(key)) forceUpdate();
        };
        map.observe(cbObserve);
        return () => {
            map.unobserve(cbObserve);
        };
    });

    const setInDoc = useMemo(
        () => (v: T) => {
            map.set(key, v);
            forceUpdate();
        },
        [map]
    );

    const value = map.get(key) ?? defaultValue;

    return [value, setInDoc];
}
