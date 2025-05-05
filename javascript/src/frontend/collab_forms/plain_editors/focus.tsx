import { CSSProperties, useCallback, useEffect, useState } from "react";
import { type Awareness } from "y-protocols/awareness.js";
import * as Y from "yjs";

type FocusAwareness = {
    relPos: unknown;
    key: string;
};

export type FocusedUser = {
    clientId: number;
    name: string;
    color: string;
};

/**
 * Listens to and publishes focus on a plain field to other YJS peers.
 * @param awareness The YJS provider awareness
 * @param map Map of plain fields
 * @param key Key of the plain field to listen to
 * @returns A structure containing: `focusedUsers`: array of users (other than the local one) that have focused this field;
 * `onFocus`/`onBlur`: Event methods for the `focus` and `blur` events.
 */
export function useYMapFocus(
    awareness: Awareness,
    map: Y.Map<any>,
    key: string
): {
    focusedUsers: FocusedUser[];
    onFocus: () => void;
    onBlur: () => void;
} {
    const [focusedUsers, setFocusedUsers] = useState<FocusedUser[]>([]);

    useEffect(() => {
        let updateFocusedUsers = () => {
            let out: FocusedUser[] = [];
            awareness.getStates().forEach((aw, clientId) => {
                if (clientId === awareness.clientID) return;

                const focus: FocusAwareness | null | undefined = aw.focus;
                if (!focus) return;

                const anchor = Y.createAbsolutePositionFromRelativePosition(
                    Y.createRelativePositionFromJSON(focus.relPos),
                    map.doc!
                );
                if (!anchor) return;
                if (anchor.type !== map) return;

                if (focus.key !== key) return;

                const name = aw.user?.name ?? `User: ${clientId}`;
                const color = aw.user?.color ?? "#ffa500";
                out.push({
                    clientId,
                    name,
                    color,
                });
            });
            out.sort((a, b) => a.clientId - b.clientId);
            setFocusedUsers(out);
        };

        updateFocusedUsers();
        awareness.on("change", updateFocusedUsers);
        return () => {
            awareness.off("change", updateFocusedUsers);
        };
    }, [awareness, map, key]);

    const onFocus = useCallback(() => {
        const field: FocusAwareness = {
            relPos: Y.relativePositionToJSON(
                Y.createRelativePositionFromTypeIndex(map, 0)
            ),
            key,
        };
        awareness.setLocalStateField("focus", field);
    }, [awareness, map, key]);

    const onBlur = useCallback(() => {
        awareness.setLocalStateField("focus", null);
    }, [awareness]);

    return {
        focusedUsers,
        onFocus,
        onBlur,
    };
}

/**
 * Renders a list of users currently focusing an element
 */
export function FocusedUsersList(props: { focusedUsers: FocusedUser[] }) {
    return (
        <ul className="list-unstyled collab-focused-users">
            {props.focusedUsers.map((v) => (
                <li key={v.clientId} style={{ backgroundColor: v.color }}>
                    {v.name}
                </li>
            ))}
        </ul>
    );
}

/**
 * Adds styles for an input element based on other users focusing on it
 * @param focusedUsers The array of other users focusing on this element
 * @param styles Optional styles object to modify. Mutated if provided.
 * @returns The `styles` argument, or a new style object if none was provided, with the appropriate styles assigned.
 */
export function setFocusStyles(
    focusedUsers: FocusedUser[],
    styles?: CSSProperties | undefined | null
): CSSProperties {
    const outStyles = styles ?? {};
    if (focusedUsers.length > 0) {
        outStyles.outline = `0.5rem solid ${focusedUsers[0].color}`;
    }
    return outStyles;
}
