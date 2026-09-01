import { faCheck } from "@fortawesome/free-solid-svg-icons/faCheck";
import { faPalette } from "@fortawesome/free-solid-svg-icons/faPalette";
import { faXmark } from "@fortawesome/free-solid-svg-icons/faXmark";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Editor } from "@tiptap/core";
import { useId, useState } from "react";
import ReactModal from "react-modal";
import { useEditorState } from "@tiptap/react";

const DEFAULT_COLOR = "#6D70A7";
const COLOR_SWATCHES = [
    { name: "Ink", value: "#202428" },
    { name: "Slate", value: "#4B5563" },
    { name: "Gray", value: "#6C809A" },
    { name: "White", value: "#FFFFFF" },
    { name: "Red", value: "#C44536" },
    { name: "Orange", value: "#F46036" },
    { name: "Gold", value: "#B7791F" },
    { name: "Green", value: "#2F7D4C" },
    { name: "Teal", value: "#287C7B" },
    { name: "Blue", value: "#4F6DB8" },
    { name: "Violet", value: "#6D70A7" },
    { name: "Orchid", value: "#947BD3" },
] as const;

function normalizeHexColor(color: string): string | null {
    const trimmed = color.trim();
    const prefixed = trimmed.startsWith("#") ? trimmed : `#${trimmed}`;

    if (/^#[0-9a-f]{6}$/i.test(prefixed)) return prefixed.toUpperCase();
    if (/^#[0-9a-f]{3}$/i.test(prefixed)) {
        const [r, g, b] = prefixed.slice(1).split("");
        return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
    }
    return null;
}

function usesDarkCheck(color: string): boolean {
    const normalized = normalizeHexColor(color);
    if (!normalized) return false;

    const red = parseInt(normalized.slice(1, 3), 16);
    const green = parseInt(normalized.slice(3, 5), 16);
    const blue = parseInt(normalized.slice(5, 7), 16);
    return red * 0.299 + green * 0.587 + blue * 0.114 > 170;
}

export type ColorModalMode = null | "new" | "edit";
export function ColorModal(props: {
    modalMode: ColorModalMode;
    setModalMode: (m: ColorModalMode) => void;
    formColor: string;
    setFormColor: (c: string) => void;
    setColor: (color: string) => void;
    removeColor: () => void;
    title?: string;
}) {
    const fieldId = useId();
    const normalizedColor = normalizeHexColor(props.formColor);
    const title = props.title ?? "Text color";

    return (
        <ReactModal
            isOpen={!!props.modalMode}
            onRequestClose={() => props.setModalMode(null)}
            contentLabel={title}
            className="modal-dialog modal-dialog-centered gw-color-dialog"
        >
            <form
                className="modal-content"
                onSubmit={(event) => {
                    event.preventDefault();
                    if (!normalizedColor) return;
                    props.setColor(normalizedColor);
                    props.setModalMode(null);
                }}
            >
                <div className="modal-header">
                    <div>
                        <h5 className="modal-title">{title}</h5>
                        <p className="gw-color-dialog-intro">
                            Choose a report-ready color or enter an exact value.
                        </p>
                    </div>
                    <button
                        type="button"
                        className="gw-color-dialog-close"
                        aria-label="Close color picker"
                        onClick={() => props.setModalMode(null)}
                    >
                        <FontAwesomeIcon icon={faXmark} />
                    </button>
                </div>

                <div className="modal-body gw-color-dialog-body">
                    <fieldset className="gw-color-palette">
                        <legend>Document palette</legend>
                        <div className="gw-color-swatches">
                            {COLOR_SWATCHES.map((swatch) => {
                                const selected =
                                    normalizedColor === swatch.value;
                                return (
                                    <button
                                        key={swatch.value}
                                        type="button"
                                        className={
                                            selected
                                                ? "gw-color-swatch is-selected"
                                                : "gw-color-swatch"
                                        }
                                        style={
                                            {
                                                "--gw-swatch-color":
                                                    swatch.value,
                                            } as React.CSSProperties
                                        }
                                        title={`${swatch.name} ${swatch.value}`}
                                        aria-label={`${swatch.name}, ${swatch.value}`}
                                        aria-pressed={selected}
                                        onClick={() =>
                                            props.setFormColor(swatch.value)
                                        }
                                    >
                                        {selected && (
                                            <FontAwesomeIcon
                                                icon={faCheck}
                                                className={
                                                    usesDarkCheck(swatch.value)
                                                        ? "use-dark-check"
                                                        : undefined
                                                }
                                            />
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    </fieldset>

                    <div className="gw-color-custom">
                        <label htmlFor={fieldId}>Custom color</label>
                        <div className="gw-color-custom-controls">
                            <input
                                type="color"
                                className="gw-color-native"
                                value={normalizedColor ?? DEFAULT_COLOR}
                                aria-label="Open custom color picker"
                                onChange={(event) =>
                                    props.setFormColor(
                                        event.target.value.toUpperCase()
                                    )
                                }
                            />
                            <div className="gw-color-hex-field">
                                <span aria-hidden="true">#</span>
                                <input
                                    id={fieldId}
                                    type="text"
                                    value={props.formColor.replace(/^#/, "")}
                                    maxLength={6}
                                    spellCheck={false}
                                    autoComplete="off"
                                    aria-describedby={`${fieldId}-help`}
                                    aria-invalid={!normalizedColor}
                                    onChange={(event) =>
                                        props.setFormColor(
                                            `#${event.target.value.replace(
                                                /[^0-9a-f]/gi,
                                                ""
                                            )}`
                                        )
                                    }
                                />
                            </div>
                        </div>
                        <span
                            id={`${fieldId}-help`}
                            className={
                                normalizedColor
                                    ? "gw-color-field-help"
                                    : "gw-color-field-help is-invalid"
                            }
                        >
                            {normalizedColor
                                ? `Selected ${normalizedColor}`
                                : "Enter a 3- or 6-digit hex color."}
                        </span>
                    </div>
                </div>

                <div className="modal-footer">
                    {props.modalMode === "edit" && (
                        <button
                            type="button"
                            className="btn btn-outline-danger me-auto"
                            onClick={() => {
                                props.removeColor();
                                props.setModalMode(null);
                            }}
                        >
                            Clear color
                        </button>
                    )}
                    <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={() => props.setModalMode(null)}
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        className="btn gw-color-apply"
                        disabled={!normalizedColor}
                    >
                        Apply color
                    </button>
                </div>
            </form>
        </ReactModal>
    );
}

export default function ColorButton({ editor }: { editor: Editor }) {
    const [modalMode, setModalMode] = useState<null | "new" | "edit">(null);
    const [formColor, setFormColor] = useState<string>(DEFAULT_COLOR);

    const { enabled, active } = useEditorState({
        editor,
        selector: ({ editor }) => {
            if (!editor.isInitialized) return { enabled: false, active: false };

            const enabled = editor
                .can()
                .chain()
                .focus()
                .setColor({ color: "#fff" })
                .run();
            const active = editor.isActive("color");
            return { enabled, active };
        },
    });

    return (
        <>
            <button
                tabIndex={-1}
                title="Color"
                type="button"
                disabled={!enabled}
                className={active ? "is-active" : undefined}
                onClick={(e) => {
                    e.preventDefault();
                    const active = editor.isActive("color");
                    if (active) {
                        editor.chain().focus().extendMarkRange("color").run();
                        setFormColor(editor.getAttributes("color").color);
                    } else {
                        setFormColor(DEFAULT_COLOR);
                    }
                    setModalMode(active ? "edit" : "new");
                }}
            >
                <FontAwesomeIcon icon={faPalette} />
            </button>
            <ColorModal
                modalMode={modalMode}
                setModalMode={setModalMode}
                formColor={formColor}
                setFormColor={setFormColor}
                setColor={(color) => {
                    editor.chain().setColor({ color }).run();
                }}
                removeColor={() => {
                    editor.chain().unsetColor().run();
                }}
            />
        </>
    );
}
