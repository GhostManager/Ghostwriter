import { useContext, useId, useState } from "react";
import ReactModal from "react-modal";
import { EvidencesContext } from "../../../../tiptap_gw/evidence";
import { Editor } from "@tiptap/react";
import EvidenceUploadForm from "./upload";

export default function EvidenceModal(props: {
    editor: Editor;
    initialId: null | number;
    initialFile?: File;
    setEvidenceId: (id: number | null) => void;
}) {
    const [uploadMode, setUploadMode] = useState<boolean>(
        props.initialFile != null
    );

    let content;
    if (uploadMode) {
        content = (
            <EvidenceUploadForm
                initialFile={props.initialFile}
                switchMode={() => setUploadMode(false)}
                onSubmit={props.setEvidenceId}
            />
        );
    } else {
        content = (
            <EvidenceSelectForm
                initial={props.initialId}
                switchMode={() => setUploadMode(true)}
                onSubmit={props.setEvidenceId}
            />
        );
    }

    const title = uploadMode
        ? "Upload evidence"
        : props.initialId === null
          ? "Insert evidence"
          : "Edit evidence reference";
    const description = uploadMode
        ? "Add a report-ready file and insert it at the current cursor position."
        : "Choose evidence already attached to this report.";

    return (
        <ReactModal
            isOpen
            onRequestClose={() => props.setEvidenceId(null)}
            contentLabel={title}
            className="modal-dialog modal-dialog-centered gw-evidence-dialog"
        >
            <div className="modal-content gw-evidence-dialog-content">
                <div className="modal-header gw-evidence-dialog-header">
                    <div>
                        <span className="gw-evidence-dialog-eyebrow">
                            Report evidence
                        </span>
                        <h5 className="modal-title">{title}</h5>
                        <p className="gw-evidence-dialog-intro">
                            {description}
                        </p>
                    </div>
                    <button
                        type="button"
                        className="gw-evidence-dialog-close"
                        aria-label="Close"
                        onClick={() => props.setEvidenceId(null)}
                    >
                        <i className="fas fa-times" aria-hidden="true" />
                    </button>
                </div>
                {content}
            </div>
        </ReactModal>
    );
}

function EvidenceSelectForm(props: {
    initial: number | null;
    onSubmit: (id: number | null) => void;
    switchMode: () => void;
}) {
    const evidences = useContext(EvidencesContext);
    const [selectedId, setSelectedId] = useState<number | null>(props.initial);
    const nameId = useId();
    return (
        <>
            <div className="modal-body gw-evidence-dialog-body">
                <div className="gw-evidence-picker">
                    <div className="gw-evidence-picker-icon" aria-hidden="true">
                        <i className="fas fa-paperclip" />
                    </div>
                    <div className="gw-evidence-picker-field">
                        <label htmlFor={nameId}>Evidence file</label>
                        <p id={`${nameId}-help`}>
                            Select the file to place at the current cursor
                            position.
                        </p>
                    </div>
                    <select
                        id={nameId}
                        className="form-select form-select-lg gw-evidence-select"
                        aria-describedby={`${nameId}-help`}
                        value={selectedId?.toString() ?? ""}
                        onChange={(e) =>
                            setSelectedId(
                                e.target.value === ""
                                    ? null
                                    : parseInt(e.target.value)
                            )
                        }
                    >
                        <option value="">Choose evidence…</option>
                        {evidences?.evidence?.map((e) => (
                            <option value={e.id} key={e.id}>
                                {e.friendlyName}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="modal-footer gw-evidence-dialog-footer">
                <button
                    type="button"
                    className="btn btn-outline-secondary gw-evidence-mode-action"
                    onClick={(e) => {
                        e.preventDefault();
                        props.switchMode();
                    }}
                >
                    <i className="fas fa-upload" aria-hidden="true" />
                    Upload new evidence
                </button>
                <div className="gw-evidence-dialog-primary-actions">
                    <button
                        type="button"
                        className="btn btn-outline-secondary"
                        onClick={(e) => {
                            e.preventDefault();
                            props.onSubmit(null);
                        }}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        className="btn gw-evidence-primary-action"
                        disabled={selectedId === null}
                        onClick={(e) => {
                            e.preventDefault();
                            props.onSubmit(selectedId);
                        }}
                    >
                        <i className="fas fa-paperclip" aria-hidden="true" />
                        {props.initial === null
                            ? "Insert evidence"
                            : "Save reference"}
                    </button>
                </div>
            </div>
        </>
    );
}
