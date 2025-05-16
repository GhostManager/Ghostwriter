/** <input> last-write-wins editors */

import * as Y from "yjs";
import { useMemo, useState } from "react";
import { HocuspocusProvider } from "@hocuspocus/provider";
import { FocusedUsersList, setFocusStyles, useYMapFocus } from "./focus";
import { usePlainField } from "./field";

export function BaseInput<T>(props: {
    provider: HocuspocusProvider;
    mapKey: string;
    connected: boolean;
    toString: (v: T) => string;
    parse: (v: string) => T | null;
    defaultValue: T;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}) {
    const map = useMemo(
        () => props.provider.document.get("plain_fields", Y.Map<any>)!,
        [props.provider]
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
                }}
                onFocus={onFocus}
                onBlur={() => {
                    onBlur();

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
            <FocusedUsersList focusedUsers={focusedUsers} />
        </>
    );
}

const identity = (v: string) => v;

export function PlainTextInput(props: {
    provider: HocuspocusProvider;
    mapKey: string;
    connected: boolean;
    inputProps?: React.InputHTMLAttributes<HTMLInputElement>;
}) {
    const inputProps = {
        type: "text",
        ...props.inputProps,
    };
    return (
        <BaseInput
            provider={props.provider}
            mapKey={props.mapKey}
            connected={props.connected}
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
    provider: HocuspocusProvider;
    mapKey: string;
    connected: boolean;
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
    provider: HocuspocusProvider;
    mapKey: string;
    connected: boolean;
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

const tryToFloat = (v: string) => {
    const n = parseFloat(v);
    return n === n ? n : null;
};

export function FloatInput(props: {
    provider: HocuspocusProvider;
    mapKey: string;
    connected: boolean;
    inputProps?: React.HTMLAttributes<HTMLInputElement>;
    defaultValue?: number;
}) {
    const inputProps = {
        type: "number",
        step: "any",
        ...props.inputProps,
    };
    return (
        <BaseInput
            {...props}
            inputProps={inputProps}
            parse={tryToFloat}
            toString={toString}
            defaultValue={props.defaultValue ?? 0}
        />
    );
}

export function CheckboxInput(props: {
    connected: boolean;
    provider: HocuspocusProvider;
    mapKey: string;
    inputProps?: React.HTMLAttributes<HTMLInputElement>;
    defaultValue?: boolean;
}) {
    const map = useMemo(
        () => props.provider.document.get("plain_fields", Y.Map<any>),
        [props.provider]
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
