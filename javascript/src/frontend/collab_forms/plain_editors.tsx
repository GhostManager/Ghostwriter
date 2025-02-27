/// Last-write-wins editors. They will sync but don't have doc-style collaborative editing - the latest update will overwrite the others.

import * as Y from "yjs";
import { useEffect, useMemo, useReducer, useState } from "react";

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

export function BaseInput<T>(props: {
    connected: boolean;
    map: Y.Map<T>;
    mapKey: string;
    toString: (v: T) => string;
    parse: (v: string) => T | null;
    defaultValue: T;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}) {
    const [docValue, setDocValue] = usePlainField<T>(
        props.map,
        props.mapKey,
        props.defaultValue
    );
    const [formValue, setFormValue] = useState<string | null>(null);

    return (
        <input
            {...props.inputProps}
            disabled={!props.connected}
            value={formValue === null ? props.toString(docValue) : formValue}
            onInput={(ev) => {
                setFormValue((ev.target as HTMLInputElement).value);
            }}
            onBlur={() => {
                if (formValue === null) return;
                const parsed = props.parse(formValue);
                if (parsed === null || parsed === docValue) {
                    setFormValue(null);
                    return;
                }
                setDocValue(parsed);
                setFormValue(null);
            }}
            onKeyUp={(ev) => {
                if (ev.key !== "Enter" || formValue === null) return;
                const parsed = props.parse(formValue);
                if (parsed === null || parsed === docValue) {
                    setFormValue(null);
                    return;
                }
                setDocValue(parsed);
                setFormValue(null);
            }}
        />
    );
}

const identity = (v: string) => v;

export function PlainTextInput(props: {
    connected: boolean;
    map: Y.Map<any>;
    mapKey: string;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
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

const toString = (v: any) => v.toString();
const tryToNumber = (v: string) => {
    const n = parseFloat(v);
    return n === n ? n : null;
};

export function NumberInput(props: {
    connected: boolean;
    map: Y.Map<any>;
    mapKey: string;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
    defaultValue?: number;
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
            defaultValue={props.defaultValue ?? 0}
        />
    );
}

const tryToInteger = (v: string) => {
    const n = parseInt(v);
    return n === n ? n : null;
};

export function IntegerInput(props: {
    connected: boolean;
    map: Y.Map<any>;
    mapKey: string;
    inputProps?: React.HTMLAttributes<HTMLInputElement>;
    defaultValue?: number;
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
            defaultValue={props.defaultValue ?? 0}
        />
    );
}

export function CheckboxInput(props: {
    connected: boolean;
    map: Y.Map<any>;
    mapKey: string;
    inputProps?: React.HTMLAttributes<HTMLInputElement>;
    defaultValue?: boolean;
}) {
    const [docValue, setDocValue] = usePlainField<boolean>(
        props.map,
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
