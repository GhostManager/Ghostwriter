import { HocuspocusProvider } from "@hocuspocus/provider";
import { Editor } from "@tiptap/core";
import { KeyboardEvent, ReactNode, useEffect, useState } from "react";

import { ConnectionStatus } from "../connection";
import { NumberInput, PlainTextInput } from "../plain_editors/input";
import { TagEditor } from "../plain_editors/tag_editor";
import RichTextEditor from "../rich_text_editor";
import ExtraFieldsSection, { useExtraFieldSpecs } from "../extra_fields";
import Dropdown from "../plain_editors/dropdown";
import { gql } from "../../../__generated__";
import {
    Get_Finding_TypesQuery,
    Get_SeveritiesQuery,
} from "../../../__generated__/graphql";
import CvssCalculator from "../plain_editors/cvss";

const GET_FINDING_TYPES = gql(`
    query GET_FINDING_TYPES {
        findingType(order_by:[{id: asc}]) {
            id, findingType
        }
    }
`);
function convertFindingTypes(data: Get_Finding_TypesQuery): [number, string][] {
    return data.findingType.map((t) => [t.id, t.findingType]);
}

const GET_SEVERITIES = gql(`
    query GET_SEVERITIES {
        findingSeverity(order_by:[{id: asc}]) {
            id, severity
        }
    }
`);
function convertSeverities(data: Get_SeveritiesQuery): [number, string][] {
    return data.findingSeverity.map((t) => [t.id, t.severity]);
}

const EMPTY = {};

type FindingFormTab = "details" | "narrative" | "technical" | "extra-fields";

const FINDING_FORM_TABS: {
    id: FindingFormTab;
    label: string;
    icon: string;
}[] = [
    { id: "details", label: "Details", icon: "fa-sliders-h" },
    { id: "narrative", label: "Narrative", icon: "fa-align-left" },
    { id: "technical", label: "Technical", icon: "fa-microscope" },
    { id: "extra-fields", label: "Extra Fields", icon: "fa-puzzle-piece" },
];

function getInitialFindingFormTab(hasExtraFields: boolean): FindingFormTab {
    const requestedTab = window.location.hash.replace(
        "#",
        ""
    ) as FindingFormTab;
    const validTabs = hasExtraFields
        ? FINDING_FORM_TABS
        : FINDING_FORM_TABS.filter((tab) => tab.id !== "extra-fields");
    return validTabs.some((tab) => tab.id === requestedTab)
        ? requestedTab
        : "details";
}

function FindingFormSection(props: {
    activeTab: FindingFormTab;
    children: ReactNode;
    id: FindingFormTab;
    tabbed: boolean;
}) {
    if (!props.tabbed) return <>{props.children}</>;

    const active = props.activeTab === props.id;
    return (
        <section
            id={`finding-form-${props.id}`}
            className={`tab-pane fade${active ? " show active" : ""}`}
            role="tabpanel"
            aria-labelledby={`finding-form-tab-${props.id}`}
            hidden={!active}
        >
            <div className="finding-form-panel">{props.children}</div>
        </section>
    );
}

export function FindingFormFields({
    provider,
    status,
    connected,
    toolbarExtra,
    extraTop,
    extraBottom,
    setEditing,
    tabbed = false,
}: {
    provider: HocuspocusProvider;
    status: ConnectionStatus;
    connected: boolean;
    toolbarExtra?: (editor: Editor) => React.ReactNode;
    extraTop?: React.ReactNode;
    extraBottom?: React.ReactNode;
    setEditing?: (editing: boolean) => void;
    tabbed?: boolean;
}) {
    const extraFieldSpecs = useExtraFieldSpecs();
    const visibleTabs = extraFieldSpecs.length
        ? FINDING_FORM_TABS
        : FINDING_FORM_TABS.filter((tab) => tab.id !== "extra-fields");
    const [activeTab, setActiveTab] = useState<FindingFormTab>(() =>
        getInitialFindingFormTab(extraFieldSpecs.length > 0)
    );

    useEffect(() => {
        if (!tabbed) return;

        const applyHash = () => {
            setActiveTab(getInitialFindingFormTab(extraFieldSpecs.length > 0));
        };
        window.addEventListener("hashchange", applyHash);
        return () => window.removeEventListener("hashchange", applyHash);
    }, [extraFieldSpecs.length, tabbed]);

    const activateTab = (tab: FindingFormTab) => {
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
        document.getElementById(`finding-form-tab-${nextTab.id}`)?.focus();
    };

    return (
        <div
            className={`finding-collab-form${tabbed ? " finding-collab-form-tabbed" : ""}`}
        >
            <ConnectionStatus status={status} />

            {tabbed && (
                <ul
                    id="tab-bar"
                    className="nav nav-tabs nav-justified finding-form-tabs"
                    role="tablist"
                    aria-label="Finding form sections"
                >
                    {visibleTabs.map((tab, index) => (
                        <li
                            className="nav-item"
                            role="presentation"
                            key={tab.id}
                        >
                            <button
                                id={`finding-form-tab-${tab.id}`}
                                type="button"
                                className={`nav-link${activeTab === tab.id ? " active" : ""}`}
                                role="tab"
                                aria-controls={`finding-form-${tab.id}`}
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
            )}

            <div
                className={
                    tabbed ? "tab-content finding-form-tab-content" : undefined
                }
            >
                <FindingFormSection
                    id="details"
                    tabbed={tabbed}
                    activeTab={activeTab}
                >
                    <h4 className="icon search-icon">Finding Details</h4>
                    <hr />

                    <div className="form-row">
                        <div className="form-group col-md-6 mb-0">
                            <div className="form-group">
                                <label htmlFor="id_title">Title</label>
                                <div>
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
                        </div>
                        <div className="form-group col-md-6 mb-0">
                            <div className="form-group">
                                <label htmlFor="id_tags">Tags</label>
                                <div>
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
                        </div>
                    </div>

                    <div className="form-row">
                        <div className="form-group col-md-6 mb-0">
                            <div className="form-group">
                                <label htmlFor="collab-form-finding-type">
                                    Finding Type
                                </label>
                                <div>
                                    <Dropdown
                                        id="collab-form-finding-type"
                                        className="form-select"
                                        provider={provider}
                                        mapKey="findingTypeId"
                                        optionsQuery={GET_FINDING_TYPES}
                                        optionsVars={EMPTY}
                                        convertOptions={convertFindingTypes}
                                        connected={connected}
                                    />
                                    <small className="form-text text-muted">
                                        Select a finding category that fits
                                    </small>
                                </div>
                            </div>
                        </div>

                        <div className="form-group col-md-6 mb-0">
                            <div className="form-group">
                                <label htmlFor="collab-form-severity">
                                    Severity
                                </label>
                                <div>
                                    <Dropdown
                                        id="collab-form-severity"
                                        className="form-select"
                                        provider={provider}
                                        mapKey="severityId"
                                        connected={connected}
                                        optionsQuery={GET_SEVERITIES}
                                        optionsVars={EMPTY}
                                        convertOptions={convertSeverities}
                                    />
                                    <small className="form-text text-muted">
                                        Select a severity rating for this
                                        finding that reflects its role in a
                                        system compromise
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="form-row">
                        <div className="form-group col-md-6 mb-0">
                            <label htmlFor="collab-form-cvss-score">
                                CVSS Score
                            </label>
                            <div>
                                <NumberInput
                                    inputProps={{
                                        id: "collab-form-cvss-score",
                                        className: "form-control numberinput",
                                    }}
                                    provider={provider}
                                    mapKey="cvssScore"
                                    connected={connected}
                                    defaultValue={null}
                                    setEditing={setEditing}
                                />
                                <small className="form-text text-muted">
                                    Set the CVSS score for this finding
                                </small>
                            </div>
                        </div>

                        <div className="form-group col-md-6 mb-0">
                            <label htmlFor="collab-form-cvss-vector">
                                CVSS Vector
                            </label>
                            <div>
                                <PlainTextInput
                                    inputProps={{
                                        id: "collab-form-cvss-vector",
                                        className: "form-control numberinput",
                                        maxLength: 255,
                                    }}
                                    connected={connected}
                                    provider={provider}
                                    mapKey="cvssVector"
                                    setEditing={setEditing}
                                />
                                <small className="form-text text-muted">
                                    Set the CVSS vector for this finding
                                </small>
                            </div>
                        </div>
                    </div>

                    <CvssCalculator
                        provider={provider}
                        connected={connected}
                        vectorKey="cvssVector"
                        scoreKey="cvssScore"
                        severityKey="severityId"
                    />

                    {extraTop}
                </FindingFormSection>

                <FindingFormSection
                    id="narrative"
                    tabbed={tabbed}
                    activeTab={activeTab}
                >
                    <h4 className="icon pencil-icon">Narrative</h4>
                    <hr />

                    <div className="form-group col-md-12">
                        <label>Description</label>
                        <div>
                            <RichTextEditor
                                provider={provider}
                                connected={connected}
                                fragment={provider.document.getXmlFragment(
                                    "description"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>

                    <div className="form-group col-md-12">
                        <label>Impact</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "impact"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>

                    {extraBottom}
                </FindingFormSection>

                <FindingFormSection
                    id="technical"
                    tabbed={tabbed}
                    activeTab={activeTab}
                >
                    <h4 className="icon shield-icon">Technical Guidance</h4>
                    <hr />

                    <div className="form-group col-md-12">
                        <label>Mitigation</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "mitigation"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>

                    <div className="form-group col-md-12">
                        <label>Replication Steps</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "replicationSteps"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>

                    <div className="form-group col-md-12">
                        <label>Host Detection Techniques</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "hostDetectionTechniques"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>

                    <div className="form-group col-md-12">
                        <label>Network Detection Techniques</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "networkDetectionTechniques"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>

                    <h4 className="icon link-icon">Reference Links</h4>
                    <hr />

                    <div className="form-group col-md-12">
                        <label>References</label>
                        <div>
                            <RichTextEditor
                                connected={connected}
                                provider={provider}
                                fragment={provider.document.getXmlFragment(
                                    "references"
                                )}
                                toolbarExtra={toolbarExtra}
                            />
                        </div>
                    </div>
                </FindingFormSection>

                <FindingFormSection
                    id="extra-fields"
                    tabbed={tabbed}
                    activeTab={activeTab}
                >
                    <ExtraFieldsSection
                        connected={connected}
                        provider={provider}
                        header={
                            <>
                                <h4 className="icon link-icon">Extra Fields</h4>
                                <hr />
                            </>
                        }
                        toolbarExtra={toolbarExtra}
                        setEditing={setEditing}
                    />
                </FindingFormSection>
            </div>
        </div>
    );
}
