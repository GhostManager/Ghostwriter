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

const CVSS_VERSION_STORAGE_KEY = "ghostwriter.cvssCalculatorVersion";

/**
 * Keep the UI aligned with the backend cvss parser and FIRST CVSS v4.0 metric values.
 * The ae-cvss-calculator metadata currently allows Safety on base SC/SI/SA,
 * so this table is the local source of truth for values the backend will accept.
 */
const CVSS4_BACKEND_METRIC_VALUES: Record<string, ReadonlySet<string>> = {
    AV: new Set(["N", "A", "L", "P"]),
    AC: new Set(["L", "H"]),
    AT: new Set(["N", "P"]),
    PR: new Set(["N", "L", "H"]),
    UI: new Set(["N", "P", "A"]),
    VC: new Set(["H", "L", "N"]),
    VI: new Set(["H", "L", "N"]),
    VA: new Set(["H", "L", "N"]),
    SC: new Set(["H", "L", "N"]),
    SI: new Set(["H", "L", "N"]),
    SA: new Set(["H", "L", "N"]),
    E: new Set(["X", "A", "P", "U"]),
    CR: new Set(["X", "H", "M", "L"]),
    IR: new Set(["X", "H", "M", "L"]),
    AR: new Set(["X", "H", "M", "L"]),
    MAV: new Set(["X", "N", "A", "L", "P"]),
    MAC: new Set(["X", "L", "H"]),
    MAT: new Set(["X", "N", "P"]),
    MPR: new Set(["X", "N", "L", "H"]),
    MUI: new Set(["X", "N", "P", "A"]),
    MVC: new Set(["X", "H", "L", "N"]),
    MVI: new Set(["X", "H", "L", "N"]),
    MVA: new Set(["X", "H", "L", "N"]),
    MSC: new Set(["X", "H", "L", "N"]),
    MSI: new Set(["X", "S", "H", "L", "N"]),
    MSA: new Set(["X", "S", "H", "L", "N"]),
    S: new Set(["X", "N", "P"]),
    AU: new Set(["X", "N", "Y"]),
    R: new Set(["X", "A", "U", "I"]),
    V: new Set(["X", "D", "C"]),
    RE: new Set(["X", "L", "M", "H"]),
    U: new Set(["X", "Clear", "Green", "Amber", "Red"]),
};

/**
 * Get the default CVSS version from the backend configuration or local storage.
 * Priority: local storage > backend config > fallback to 3.1
 */
function getCvssDefaultVersion(): "3.1" | "4.0" {
    // Check local storage first
    try {
        const storedVersion = localStorage.getItem(CVSS_VERSION_STORAGE_KEY);
        if (storedVersion === "3.1" || storedVersion === "4.0") {
            return storedVersion;
        }
    } catch (e) {
        // localStorage may throw in privacy mode, blocked third-party storage, or quota exceeded
        console.warn("Could not access localStorage for CVSS version preference:", e);
    }

    // Fall back to backend config
    const defaultVersionEl = document.getElementById("default-cvss-version");
    if (defaultVersionEl) {
        const backendDefault = defaultVersionEl.textContent?.trim();
        if (backendDefault === "3.1" || backendDefault === "4.0") {
            return backendDefault;
        }
    }

    // Ultimate fallback
    return "3.1";
}

/**
 * Save CVSS version preference to local storage
 */
function saveCvssVersionPreference(version: "3.1" | "4.0") {
    try {
        localStorage.setItem(CVSS_VERSION_STORAGE_KEY, version);
    } catch (e) {
        // localStorage may throw in privacy mode, blocked third-party storage, or quota exceeded
        console.warn("Could not save CVSS version preference to localStorage:", e);
    }
}

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

    const [editingVector, setEditingVector] = useState<Vector>(() => {
        const parsed = stringToVector(docValue);
        if (parsed) return parsed;

        // No existing vector - use default version preference
        const defaultVersion = getCvssDefaultVersion();
        return defaultVersion === "4.0" ? new Cvss4P0() : new Cvss3P1();
    });

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
                        let score: number;
                        let severity: keyof typeof SEVERITY_TO_ID;
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
        <div className="card mb-2 mt-3">
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
        else if (s.startsWith("CVSS:4.0/")) {
            if (!isBackendCompatibleCvss4Vector(s)) return null;
            return new Cvss4P0(s);
        }
        return null;
    } catch (e) {
        console.error(
            "Could not parse CVSS vector (might be a bug or bad input): ",
            e
        );
        return null;
    }
}

/**
 * Reject malformed or backend-incompatible v4 vectors before passing them to
 * ae-cvss-calculator, which may accept values the Python cvss parser rejects.
 */
function isBackendCompatibleCvss4Vector(s: string): boolean {
    if (!s.startsWith("CVSS:4.0/")) return false;

    const seenMetrics = new Set<string>();
    for (const field of s.split("/").slice(1)) {
        const parts = field.split(":");
        if (parts.length !== 2) return false;

        const [metric, value] = parts;
        const allowedValues = CVSS4_BACKEND_METRIC_VALUES[metric];
        if (
            !metric ||
            !value ||
            seenMetrics.has(metric) ||
            !allowedValues ||
            !allowedValues.has(value)
        ) {
            return false;
        }
        seenMetrics.add(metric);
    }

    return true;
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
                    saveCvssVersionPreference("4.0");
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
                    saveCvssVersionPreference("3.1");
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
            {getBackendCompatibleValues(props.vector, props.component)
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

/**
 * Filter CVSS v4 buttons to values the report export parser accepts.
 * CVSS v3 components are returned unchanged because the frontend and backend
 * already agree on those metric value sets.
 */
function getBackendCompatibleValues(
    vector: Vector,
    component: VectorComponent<VectorComponentValue>
): VectorComponentValue[] {
    if (!(vector instanceof Cvss4P0)) return component.values;

    const allowedValues = CVSS4_BACKEND_METRIC_VALUES[component.shortName];
    if (!allowedValues) return component.values;

    return component.values.filter((value) =>
        allowedValues.has(value.shortName)
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
