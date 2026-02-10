import { useState } from "react";
import ReactModal from "react-modal";
import type { AcronymExpansion } from "../../../tiptap_gw/text_expansion";

interface TextExpansionModalProps {
    word: string;
    matches: AcronymExpansion[];
    onSelect: (expansion: AcronymExpansion) => void;
    onCancel: () => void;
}

export default function TextExpansionModal({
    word,
    matches,
    onSelect,
    onCancel,
}: TextExpansionModalProps) {
    const [selectedIndex, setSelectedIndex] = useState(0);

    const handleExpand = () => {
        onSelect(matches[selectedIndex]);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            e.preventDefault();
            handleExpand();
        } else if (e.key === "Escape") {
            e.preventDefault();
            onCancel();
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setSelectedIndex((prev) => Math.max(0, prev - 1));
        } else if (e.key === "ArrowDown") {
            e.preventDefault();
            setSelectedIndex((prev) => Math.min(matches.length - 1, prev + 1));
        }
    };

    return (
        <ReactModal
            isOpen={true}
            onRequestClose={onCancel}
            contentLabel={`Expand "${word}"`}
            className="modal-dialog modal-dialog-centered"
            onAfterOpen={() => {
                // Focus the modal for keyboard navigation
                document
                    .querySelector(".modal-content")
                    ?.querySelector("input")
                    ?.focus();
            }}
        >
            <div className="modal-content" onKeyDown={handleKeyDown}>
                <div className="modal-header">
                    <h5 className="modal-title">Expand &ldquo;{word}&rdquo;</h5>
                    <button
                        type="button"
                        className="close"
                        onClick={onCancel}
                        aria-label="Close"
                    >
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div className="modal-body">
                    <p className="text-muted mb-3">
                        Multiple expansions found. Select one:
                    </p>
                    <div className="list-group">
                        {matches.map((match, index) => (
                            <label
                                key={index}
                                className={`list-group-item list-group-item-action ${
                                    selectedIndex === index ? "active" : ""
                                }`}
                                style={{ cursor: "pointer" }}
                            >
                                <input
                                    type="radio"
                                    name="expansion"
                                    value={index}
                                    checked={selectedIndex === index}
                                    onChange={() => setSelectedIndex(index)}
                                    className="mr-2"
                                    style={{ marginRight: "0.5rem" }}
                                />
                                <strong>{match.full}</strong>
                            </label>
                        ))}
                    </div>
                </div>
                <div className="modal-footer">
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={onCancel}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        className="btn btn-primary"
                        onClick={handleExpand}
                    >
                        Expand
                    </button>
                </div>
            </div>
        </ReactModal>
    );
}
