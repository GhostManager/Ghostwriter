import { createRoot } from "react-dom/client";
import { KeyboardEvent, ReactNode, useEffect, useState } from "react";

import { ConnectionStatus, usePageConnection } from "../connection";
import { PlainTextInput } from "../plain_editors/input";
import { TagEditor } from "../plain_editors/tag_editor";
import RichTextEditor from "../rich_text_editor";
import ExtraFieldsSection, { useExtraFieldSpecs } from "../extra_fields";
import ReactModal from "react-modal";
import ErrorBoundary from "../error_boundary";

type ObservationFormTab = "observation" | "extra-fields";

const OBSERVATION_FORM_TABS: {
    id: ObservationFormTab;
    label: string;
    icon: string;
}[] = [
    { id: "observation", label: "Observation", icon: "fa-align-left" },
    { id: "extra-fields", label: "Extra Fields", icon: "fa-puzzle-piece" },
];

function getInitialObservationFormTab(
    hasExtraFields: boolean
): ObservationFormTab {
    const requestedTab = window.location.hash.replace(
        "#",
        ""
    ) as ObservationFormTab;
    const validTabs = hasExtraFields
        ? OBSERVATION_FORM_TABS
        : OBSERVATION_FORM_TABS.filter((tab) => tab.id !== "extra-fields");

    return validTabs.some((tab) => tab.id === requestedTab)
        ? requestedTab
        : "observation";
}

function ObservationFormSection(props: {
    activeTab: ObservationFormTab;
    children: ReactNode;
    id: ObservationFormTab;
}) {
    const active = props.activeTab === props.id;

    return (
        <section
            id={`observation-form-${props.id}`}
            className={`tab-pane fade${active ? " show active" : ""}`}
            role="tabpanel"
            aria-labelledby={`observation-form-tab-${props.id}`}
            hidden={!active}
        >
            <div className="finding-form-panel observation-form-panel">
                {props.children}
            </div>
        </section>
    );
}

function ObservationForm() {
    const { provider, status, connected, setEditing } = usePageConnection({
        model: "observation",
    });
    const extraFieldSpecs = useExtraFieldSpecs();
    const visibleTabs = extraFieldSpecs.length
        ? OBSERVATION_FORM_TABS
        : OBSERVATION_FORM_TABS.filter((tab) => tab.id !== "extra-fields");
    const [activeTab, setActiveTab] = useState<ObservationFormTab>(() =>
        getInitialObservationFormTab(extraFieldSpecs.length > 0)
    );

    useEffect(() => {
        const applyHash = () => {
            setActiveTab(
                getInitialObservationFormTab(extraFieldSpecs.length > 0)
            );
        };
        window.addEventListener("hashchange", applyHash);
        return () => window.removeEventListener("hashchange", applyHash);
    }, [extraFieldSpecs.length]);

    const activateTab = (tab: ObservationFormTab) => {
        setActiveTab(tab);
        if (window.location.hash !== `#${tab}`) {
            window.history.pushState(null, "", `#${tab}`);
        }
    };

    const handleTabKeyDown = (
        event: KeyboardEvent<HTMLButtonElement>,
        currentIndex: number
    ) => {
        let nextIndex = currentIndex;
        if (event.key === "ArrowRight") {
            nextIndex = (currentIndex + 1) % visibleTabs.length;
        } else if (event.key === "ArrowLeft") {
            nextIndex =
                (currentIndex - 1 + visibleTabs.length) % visibleTabs.length;
        } else if (event.key === "Home") {
            nextIndex = 0;
        } else if (event.key === "End") {
            nextIndex = visibleTabs.length - 1;
        } else {
            return;
        }

        event.preventDefault();
        const nextTab = visibleTabs[nextIndex];
        activateTab(nextTab.id);
        document.getElementById(`observation-form-tab-${nextTab.id}`)?.focus();
    };

    return (
        <div className="finding-collab-form observation-collab-form">
            <ConnectionStatus status={status} />

            <ul
                id="tab-bar"
                className="nav nav-tabs nav-justified finding-form-tabs observation-form-tabs"
                role="tablist"
                aria-label="Observation form sections"
            >
                {visibleTabs.map((tab, index) => (
                    <li className="nav-item" role="presentation" key={tab.id}>
                        <button
                            id={`observation-form-tab-${tab.id}`}
                            type="button"
                            className={`nav-link${activeTab === tab.id ? " active" : ""}`}
                            role="tab"
                            aria-controls={`observation-form-${tab.id}`}
                            aria-selected={activeTab === tab.id}
                            tabIndex={activeTab === tab.id ? 0 : -1}
                            onClick={() => activateTab(tab.id)}
                            onKeyDown={(event) =>
                                handleTabKeyDown(event, index)
                            }
                        >
                            <i
                                className={`fas ${tab.icon}`}
                                aria-hidden="true"
                            />
                            <span>{tab.label}</span>
                            {tab.id === "extra-fields" && (
                                <span className="badge">
                                    {extraFieldSpecs.length}
                                </span>
                            )}
                        </button>
                    </li>
                ))}
            </ul>

            <div className="tab-content finding-form-tab-content observation-form-tab-content">
                <ObservationFormSection id="observation" activeTab={activeTab}>
                    <h4 className="icon writing-icon">Observation Content</h4>
                    <hr />

                    <div className="form-row">
                        <div className="form-group col-md-6 mb-0">
                            <div className="form-group">
                                <label htmlFor="id_title">Title</label>
                                <PlainTextInput
                                    inputProps={{
                                        id: "id_title",
                                        className: "form-control",
                                    }}
                                    connected={connected}
                                    provider={provider}
                                    mapKey="title"
                                    setEditing={setEditing}
                                />
                            </div>
                        </div>
                        <div className="form-group col-md-6 mb-0">
                            <div className="form-group">
                                <label htmlFor="id_tags">Tags</label>
                                <TagEditor
                                    id="id_tags"
                                    className="form-control"
                                    connected={connected}
                                    provider={provider}
                                    docKey="tags"
                                />
                                <small className="form-text text-muted">
                                    Separate tags with commas
                                </small>
                            </div>
                        </div>

                        <div className="form-group col-md-12">
                            <label>Description</label>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "description"
                                )}
                            />
                        </div>
                    </div>
                </ObservationFormSection>

                {extraFieldSpecs.length > 0 && (
                    <ObservationFormSection
                        id="extra-fields"
                        activeTab={activeTab}
                    >
                        <div className="observation-extra-fields-heading">
                            <div>
                                <h4 className="icon custom-field-icon">
                                    Extra Fields
                                </h4>
                                <p className="form-text mb-0">
                                    Project-specific metadata and supporting
                                    context for this observation.
                                </p>
                            </div>
                            <span className="badge extra-field-count">
                                {extraFieldSpecs.length}{" "}
                                {extraFieldSpecs.length === 1
                                    ? "field"
                                    : "fields"}
                            </span>
                        </div>
                        <hr />

                        <div className="form-row observation-extra-fields-grid">
                            <ExtraFieldsSection
                                connected={connected}
                                provider={provider}
                                setEditing={setEditing}
                            />
                        </div>
                    </ObservationFormSection>
                )}
            </div>
        </div>
    );
}

document.addEventListener("DOMContentLoaded", () => {
    ReactModal.setAppElement(
        document.querySelector("div.wrapper") as HTMLElement
    );
    const root = createRoot(document.getElementById("collab-form-container")!);
    root.render(
        <ErrorBoundary>
            <ObservationForm />
        </ErrorBoundary>
    );
});
