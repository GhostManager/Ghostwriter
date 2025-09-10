/** <input> last-write-wins editors */

import * as Y from "yjs";
import { useMemo, useState } from "react";
import { HocuspocusProvider } from "@hocuspocus/provider";
import { FocusedUsersList, setFocusStyles, useYMapFocus } from "./focus";
import { usePlainField } from "./field";

export function BaseInput<T>(props: {
    provider: HocuspocusProvider;
    map?: Y.Map<any>;
    mapKey: string;
    connected: boolean;
    toString: (v: T) => string;
    parse: (v: string) => T | undefined;
    defaultValue: T;
    setEditing?: (editing: boolean) => void;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}) {
    const map = useMemo(
        () =>
            props.map ??
            props.provider.document.get("plain_fields", Y.Map<any>)!,
        [props.map, props.provider]
    );
    const [docValue, setDocValue] = usePlainField<T>(
        map,
        props.mapKey,
        props.defaultValue
    );
    const [formValue, setFormValue] = useState<string | null>(null);
    const { focusedUsers, onFocus, onBlur } = useYMapFocus(
        props.provider.awareness!,
        map,
        props.mapKey
    );

    const style = setFocusStyles(focusedUsers, props.inputProps?.style);

    const materializeValue = () => {
        if (formValue === null) return;
        let parsed = props.parse(formValue);
        if (parsed === undefined || parsed === docValue) {
            if (props.setEditing) props.setEditing(false);
            setFormValue(null);
            return;
        } else if (parsed === null) {
            parsed = props.defaultValue;
        }
        setDocValue(parsed);
        setFormValue(null);
        if (props.setEditing) props.setEditing(false);
    };

    return (
        <>
            <input
                {...props.inputProps}
                style={style}
                disabled={!props.connected}
                value={
                    formValue === null ? props.toString(docValue) : formValue
                }
                onInput={(ev) => {
                    setFormValue((ev.target as HTMLInputElement).value);
                    if (props.setEditing) props.setEditing(true);
                }}
                onFocus={onFocus}
                onBlur={() => {
                    onBlur();
                    materializeValue();
                }}
                onKeyUp={(ev) => {
                    if (ev.key !== "Enter" || formValue === null) return;
                    materializeValue();
                }}
            />
            <FocusedUsersList focusedUsers={focusedUsers} />
        </>
    );
}

const identity = (v: string) => v;

export function PlainTextInput(props: {
    provider: HocuspocusProvider;
    map?: Y.Map<any>;
    mapKey: string;
    connected: boolean;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
    setEditing?: (editing: boolean) => void;
}) {
    const inputProps = {
        type: "text",
        ...props.inputProps,
    };
    return (
        <BaseInput
            {...props}
            inputProps={inputProps}
            parse={identity}
            toString={identity}
            defaultValue={""}
        />
    );
}

const toString = (v: any) => (v === null ? "" : v.toString());
const tryToNumber = (v: string) => {
    v = v.trim();
    if (v === "") return null;
    const n = parseFloat(v);
    return n === n ? n : undefined;
};

export function NumberInput(props: {
    provider: HocuspocusProvider;
    map?: Y.Map<any>;
    mapKey: string;
    connected: boolean;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
    defaultValue: number | null;
    setEditing?: (editing: boolean) => void;
}) {
    const inputProps = {
        type: "number",
        step: props.inputProps?.step ?? "any",
        ...props.inputProps,
    };
    return (
        <BaseInput
            {...props}
            inputProps={inputProps}
            parse={tryToNumber}
            toString={toString}
            defaultValue={props.defaultValue}
        />
    );
}

const tryToInteger = (v: string) => {
    v = v.trim();
    if (v === "") return null;
    const n = parseInt(v);
    return n === n ? n : undefined;
};

export function IntegerInput(props: {
    provider: HocuspocusProvider;
    map?: Y.Map<any>;
    mapKey: string;
    connected: boolean;
    inputProps?: React.HTMLAttributes<HTMLInputElement>;
    defaultValue: number;
    setEditing?: (editing: boolean) => void;
}) {
    const inputProps = {
        type: "number",
        ...props.inputProps,
    };
    return (
        <BaseInput
            {...props}
            inputProps={inputProps}
            parse={tryToInteger}
            toString={toString}
            defaultValue={props.defaultValue}
        />
    );
}

export function CheckboxInput(props: {
    connected: boolean;
    provider: HocuspocusProvider;
    map?: Y.Map<any>;
    mapKey: string;
    inputProps?: React.HTMLAttributes<HTMLInputElement>;
    defaultValue?: boolean;
}) {
    const map = useMemo(
        () =>
            props.map ??
            props.provider.document.get("plain_fields", Y.Map<any>),
        [props.map, props.provider]
    );
    const [docValue, setDocValue] = usePlainField<boolean>(
        map,
        props.mapKey,
        props.defaultValue ?? false
    );

    return (
        <input
            type="checkbox"
            {...props.inputProps}
            disabled={!props.connected}
            checked={docValue}
            onChange={(ev) => {
                setDocValue((ev.target as HTMLInputElement).checked);
            }}
        />
    );
}
