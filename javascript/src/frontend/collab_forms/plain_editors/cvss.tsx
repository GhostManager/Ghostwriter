import "./cvss.scss";

import * as Y from "yjs";
import { HocuspocusProvider } from "@hocuspocus/provider";
import {
    MouseEventHandler,
    useCallback,
    useEffect,
    useMemo,
    useState,
} from "react";
import { usePlainField } from "./field";

import { Cvss3P1, Cvss4P0 } from "ae-cvss-calculator";
import {
    ComponentCategory,
    type VectorComponent,
    type VectorComponentValue,
} from "ae-cvss-calculator/dist/types/src/CvssVector";
import {
    CriticalSeverityType,
    HighSeverityType,
    LowSeverityType,
    MediumSeverityType,
    NoneSeverityType,
} from "ae-cvss-calculator/dist/types/src/cvss4p0/Cvss4P0";

type Vector = Cvss3P1 | Cvss4P0;
type SetVector = (cb: (v: Vector) => Vector) => void;

// IDs taken from the fixture at reporting/fixtures/initial.json
const SEVERITY_TO_ID: {
    [k in
        | NoneSeverityType
        | LowSeverityType
        | MediumSeverityType
        | HighSeverityType
        | CriticalSeverityType]: number;
} = {
    NONE: 1,
    LOW: 2,
    MEDIUM: 3,
    HIGH: 4,
    CRITICAL: 5,
};

/**
 * CVSS calculator widget that reads/edits plain fields in a ydoc.
 */
export default function CvssCalculator(props: {
    provider: HocuspocusProvider;
    vectorKey: string;
    scoreKey: string;
    severityKey: string;
    connected: boolean;
}) {
    const map = useMemo(
        () => props.provider.document.get("plain_fields", Y.Map<any>)!,
        [props.provider]
    );
    const [docValue, setDocValue] = usePlainField<string>(
        map,
        props.vectorKey,
        ""
    );

    const [editingVector, setEditingVector] = useState<Vector>(
        () => stringToVector(docValue) ?? new Cvss3P1()
    );
    useEffect(() => {
        setEditingVector((old) => stringToVector(docValue) ?? old);
    }, [setEditingVector, docValue]);

    const [open, setOpen] = useState(false);

    const setVector: SetVector = useCallback(
        (cb) => {
            setEditingVector((old) => {
                const next = cb(old);
                if (next.isBaseFullyDefined()) {
                    // can't set inside of another set call
                    setTimeout(() => {
                        setDocValue(next.toString(false, undefined, true));
                        const scores = next.createJsonSchema();
                        let score, severity;
                        if (scores.version === "3.1") {
                            if (scores.environmentalScore !== undefined) {
                                score = scores.environmentalScore;
                                severity = scores.environmentalSeverity!;
                            } else if (scores.temporalScore !== undefined) {
                                score = scores.temporalScore;
                                severity = scores.temporalSeverity!;
                            } else {
                                score = scores.baseScore;
                                severity = scores.baseSeverity;
                            }
                        } else {
                            score = scores.baseScore!;
                            severity = scores.baseSeverity!;
                        }
                        map.set(props.scoreKey, score);
                        map.set(props.severityKey, SEVERITY_TO_ID[severity]);
                    });
                }
                return next;
            });
        },
        [map, setDocValue, setEditingVector, props.scoreKey, props.severityKey]
    );

    let form;
    if (editingVector instanceof Cvss3P1) {
        form = (
            <CvssV3Form
                vector={editingVector}
                setVector={setVector}
                connected={props.connected}
            />
        );
    } else {
        form = (
            <CvssV4Form
                vector={editingVector}
                setVector={setVector}
                connected={props.connected}
            />
        );
    }

    return (
        <div className="card mb-2">
            <div
                className={
                    "card-header library-filter d-flex " +
                    (open ? "" : "collapsed")
                }
                aria-expanded={open ? "true" : "false"}
                onClick={(e) => {
                    e.preventDefault();
                    setOpen((v) => !v);
                }}
            >
                <h5 className="mb-0 flex-grow-1">CVSS Calculator</h5>
                <span>{open ? "\u2212" : "\u002b"}</span>
            </div>
            <div
                id="cvss-calculator"
                className={open ? "collapse show" : "collapse"}
            >
                <div className="card-body">{form}</div>
            </div>
        </div>
    );
}

function stringToVector(s: string): Vector | null {
    try {
        if (s.startsWith("CVSS:3.1/")) return new Cvss3P1(s);
        else if (s.startsWith("CVSS:4.0/")) return new Cvss4P0(s);
        return null;
    } catch(e) {
        console.error("Could not parse CVSS vector (might be a bug or bad input): ", e);
        return null;
    }
}

function CvssV3Form(props: {
    vector: Cvss3P1;
    setVector: (cb: (v: Cvss4P0 | Cvss3P1) => Cvss4P0 | Cvss3P1) => void;
    connected: boolean;
}) {
    const hasBase = props.vector.isBaseFullyDefined();
    const json = props.vector.createJsonSchema();

    return (
        <div id="cvss-v3-calculator" className="form-row cvss-calculator">
            <h2>CVSS v3.1</h2>
            <button
                className="mt-2 mb-2 btn btn-outline-secondary cvss-switch"
                onClick={(e) => {
                    e.preventDefault();
                    props.setVector(() => new Cvss4P0());
                }}
            >
                Switch to v4
            </button>

            <div className="cvss-buttons">
                <CvssButtons
                    vector={props.vector}
                    setVector={props.setVector}
                    connected={props.connected}
                />
            </div>

            <div className="cvss-score-ratings">
                <ScoreCard
                    header="Base"
                    score={hasBase ? json.baseScore : undefined}
                    severity={hasBase ? json.baseSeverity : undefined}
                />
                <ScoreCard
                    header="Temporal"
                    score={json.temporalScore}
                    severity={json.temporalSeverity}
                />
                <ScoreCard
                    header="Env"
                    score={json.environmentalScore}
                    severity={json.environmentalSeverity}
                />
            </div>
        </div>
    );
}

function CvssV4Form(props: {
    vector: Cvss4P0;
    setVector: SetVector;
    connected: boolean;
}) {
    const hasBase = props.vector.isBaseFullyDefined();
    const json = props.vector.createJsonSchema();

    return (
        <div id="cvss-v4-calculator" className="form-row cvss-calculator">
            <h2>CVSS v4</h2>
            <button
                className="mt-2 mb-2 btn btn-outline-secondary cvss-switch"
                onClick={(e) => {
                    e.preventDefault();
                    props.setVector(() => new Cvss3P1());
                }}
            >
                Switch to v3
            </button>

            <div className="cvss-buttons">
                <CvssButtons
                    vector={props.vector}
                    setVector={props.setVector}
                    connected={props.connected}
                />
            </div>

            <div className="cvss-score-ratings">
                <ScoreCard
                    header="Base"
                    score={hasBase ? json.baseScore : undefined}
                    severity={hasBase ? json.baseSeverity : undefined}
                />
            </div>
        </div>
    );
}

function ScoreCard(props: {
    header: string;
    score?: number | undefined;
    severity?: string | undefined;
}) {
    return (
        <div
            className={
                props.severity !== undefined
                    ? "cvss-severity-" + props.severity
                    : undefined
            }
        >
            <h4>{props.header}</h4>
            {props.score !== undefined && (
                <span className="cvss-rating-score">{props.score}</span>
            )}
            <span
                className={
                    props.severity === undefined
                        ? "cvss-rating-severity cvss-no-severity"
                        : "cvss-rating-severity"
                }
            >
                {props.severity ?? "Select values to see score"}
            </span>
        </div>
    );
}

function CvssButtons(props: {
    vector: Vector;
    setVector: SetVector;
    connected: boolean;
}) {
    return (
        <>
            {Array.from(props.vector.getRegisteredComponents().entries()).map(
                ([category, components], i) => (
                    <CvssCategoryButtons
                        key={category.name}
                        vector={props.vector}
                        setVector={props.setVector}
                        connected={props.connected}
                        category={category}
                        components={components}
                    />
                )
            )}
        </>
    );
}

function CvssCategoryButtons(props: {
    vector: Vector;
    setVector: SetVector;
    connected: boolean;
    category: ComponentCategory;
    components: VectorComponent<VectorComponentValue>[];
}) {
    let categoryName;
    if (props.category.name === "environmental-base")
        categoryName = "Environmental (Modified Base Metrics)";
    else if (props.category.name === "environmental-security-requirement")
        categoryName = "Environmental (Security Requirements)";
    else categoryName = capitalize(props.category.name);

    const subcategories = useMemo(
        () =>
            Array.from(
                groupBy(props.components, (c) => c.subCategory).entries()
            ),
        [props.components]
    );
    return (
        <>
            <h3 className="cvss-category-header">{capitalize(categoryName)}</h3>
            {subcategories.map(([title, components], i) => (
                <CvssSubcategoryButtons
                    key={i}
                    vector={props.vector}
                    setVector={props.setVector}
                    connected={props.connected}
                    category={props.category}
                    title={title}
                    components={components}
                />
            ))}
        </>
    );
}

function CvssSubcategoryButtons(props: {
    vector: Vector;
    setVector: SetVector;
    connected: boolean;
    category: ComponentCategory;
    title: string | undefined;
    components: VectorComponent<VectorComponentValue>[];
}) {
    return (
        <>
            {props.title && (
                <h4 className="cvss-subcategory-header">{props.title}</h4>
            )}
            {props.components.map((component, i) => (
                <CvssRowButtons
                    key={i}
                    vector={props.vector}
                    setVector={props.setVector}
                    connected={props.connected}
                    category={props.category}
                    component={component}
                />
            ))}
        </>
    );
}

function CvssRowButtons(props: {
    vector: Vector;
    setVector: SetVector;
    connected: boolean;
    category: ComponentCategory;
    component: VectorComponent<VectorComponentValue>;
}) {
    return (
        <>
            <h5
                title={props.component.description}
                className="cvss-metric-name"
            >
                {props.component.name}
            </h5>
            {props.component.values
                .filter(
                    (value) =>
                        props.category.name !== "base" ||
                        value.shortName !== "X"
                )
                .map((value, i) => (
                    <CvssButton
                        key={i}
                        component={props.component}
                        value={value}
                        editingVector={props.vector}
                        setVector={props.setVector}
                        connected={props.connected}
                    />
                ))}
        </>
    );
}

function CvssButton(props: {
    component: VectorComponent<VectorComponentValue>;
    value: VectorComponentValue;
    editingVector: Vector;
    setVector: SetVector;
    connected: boolean;
}) {
    const click: MouseEventHandler = useCallback(
        (ev) => {
            ev.preventDefault();
            props.setVector((old) => {
                const next = old.clone() as Vector;
                next.applyComponent(props.component, props.value);
                return next;
            });
        },
        [props.component, props.value, props.setVector]
    );

    const editingValue = props.editingVector.getComponent(props.component);

    const selected = editingValue
        ? editingValue.name === props.value.name
        : false;
    return (
        <button
            onClick={click}
            className={
                selected
                    ? "btn btn-primary btn-sm cvss-button cvss-button-selected"
                    : "btn btn-outline-secondary btn-sm cvss-button"
            }
            disabled={!props.connected}
        >
            {props.value.name} ({props.value.shortName})
        </button>
    );
}

function capitalize(s: string): string {
    return s.substring(0, 1).toUpperCase() + s.substring(1);
}

function groupBy<T, K>(arr: Iterable<T>, key: (v: T) => K): Map<K, T[]> {
    const map = new Map<K, T[]>();
    for (const v of arr) {
        const k = key(v);
        if (!map.has(k)) map.set(k, []);
        map.get(k)!.push(v);
    }
    return map;
}
