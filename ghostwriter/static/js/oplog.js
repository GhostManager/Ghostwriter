/* JavaScript specific to the log entry view page goes here. */
$(document).ready(function () {
    const $splitContainer = $('.oplog-split-container');
    const $listPane = $('#oplogListPane');
    const $listScroll = $('#oplogListScroll');
    const $table = $('#oplogTable');
    const $tableBody = $('#oplogTableBody');
    const $tableHeader = $('#oplogTableHeader');
    const $tableHeaderHidden = $('#oplogTableHeaderHidden');
    const $detailPane = $('#oplogDetailPane');
    const $detailEmpty = $('#oplogDetailEmpty');
    const $detailContent = $('#oplogDetailContent');
    const $checkboxList = $('#checkboxList');
    const $connectionStatus = $('#connectionStatus');
    const $sanitizeCheckboxList = $('#sanitize-checklist-form');
    const $searchInput = $('#searchInput');
    const $oplogTableNoEntries = $('#oplogTableNoEntries');
    const $oplogTableLoading = $('#oplogTableLoading');
    const $clearSearchBtn = $('#clearSearchBtn');

    // Track columns hidden by the user (overrides showByDefault: true)
    let hiddenLogTblColumns = JSON.parse(localStorage.getItem('hiddenLogTblColumns') || '[]');
    // Track columns explicitly shown by the user (overrides showByDefault: false)
    let shownLogTblColumns = JSON.parse(localStorage.getItem('shownLogTblColumns') || '[]');

    const oplog_entry_extra_fields_spec = JSON.parse(
        document.getElementById('oplog_entry_extra_fields_spec').textContent
    );

    const oplog_name = $splitContainer.attr('data-oplog-name');
    const oplog_id = parseInt($splitContainer.attr('data-oplog-id'));

    let socket = null;
    let allEntriesFetched = false;
    let errorDisplayed = false;
    let pendingOperation = null;
    let selectedEntryId = null;

    // Deep-link support: read ?entry=<id>#entry-<id> from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const deepLinkEntryId = parseInt(urlParams.get('entry') || '0') || null;
    let deepLinkResolved = false;

    // Store all entry data keyed by ID
    let entryDataStore = {};

    // --- Column definitions ---
    // Summary columns shown in the left list
    let summaryColumns = [
        {
            checkBoxID: 'startDateCheckBox',
            columnClass: 'startDateColumn',
            prettyName: 'Start Date',
            internalName: 'start_date',
            toHtml: v => formatDate(v),
            showByDefault: true,
            sanitizeByDefault: false,
        },
        {
            checkBoxID: 'endDateCheckBox',
            columnClass: 'endDateColumn',
            prettyName: 'End Date',
            internalName: 'end_date',
            toHtml: v => formatDate(v),
            showByDefault: false,
            sanitizeByDefault: false,
        },
        {
            checkBoxID: 'sourceIPCheckbox',
            columnClass: 'sourceIPColumn',
            prettyName: 'Source',
            internalName: 'source_ip',
            toHtml: v => `<span class="oplog-source-dest">${jsEscape(v)}</span>`,
            showByDefault: false,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'destIPCheckbox',
            columnClass: 'destIPColumn',
            prettyName: 'Dest',
            internalName: 'dest_ip',
            toHtml: v => `<span class="oplog-source-dest">${jsEscape(v)}</span>`,
            showByDefault: true,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'toolNameCheckbox',
            columnClass: 'toolNameColumn',
            prettyName: 'Tool',
            internalName: 'tool',
            showByDefault: true,
            sanitizeByDefault: false,
        },
        {
            checkBoxID: 'userContextCheckbox',
            columnClass: 'userContextColumn',
            prettyName: 'User Context',
            internalName: 'user_context',
            toHtml: v => `<span class="oplog-source-dest">${jsEscape(v)}</span>`,
            showByDefault: false,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'commandCheckbox',
            columnClass: 'commandColumn',
            prettyName: 'Command',
            internalName: 'command',
            toHtml: v => jsEscape(truncateText(v, 100)),
            showByDefault: false,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'outputCheckbox',
            columnClass: 'outputColumn',
            prettyName: 'Output',
            internalName: 'output',
            toHtml: v => jsEscape(truncateText(v, 100)),
            showByDefault: false,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'descriptionCheckbox',
            columnClass: 'descriptionColumn',
            prettyName: 'Description',
            internalName: 'description',
            toHtml: v => {
                if (!v) return '';
                let safe = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(v) : jsEscape(v);
                return jsEscape(truncateText($('<div>').html(safe).text(), 100));
            },
            showByDefault: false,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'commentsCheckbox',
            columnClass: 'commentsColumn',
            prettyName: 'Comments',
            internalName: 'comments',
            toHtml: v => {
                if (!v) return '';
                let safe = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(v) : jsEscape(v);
                return jsEscape(truncateText($('<div>').html(safe).text(), 100));
            },
            showByDefault: false,
            sanitizeByDefault: true,
        },
        {
            checkBoxID: 'operatorCheckbox',
            columnClass: 'operatorColumn',
            prettyName: 'Operator',
            internalName: 'operator_name',
            showByDefault: true,
            sanitizeByDefault: false,
        },
        {
            checkBoxID: 'tagsCheckbox',
            columnClass: 'tagsColumn',
            prettyName: 'Tags',
            internalName: 'tags',
            toHtml: v => stylizeTags(jsEscape(v)),
            showByDefault: true,
            sanitizeByDefault: false,
        },
    ];

    // Detail-only fields shown in the right viewer
    let detailFields = [
        { internalName: 'command', prettyName: 'Command', type: 'code', sanitizeByDefault: true },
        { internalName: 'output', prettyName: 'Output', type: 'code', sanitizeByDefault: true },
        { internalName: 'description', prettyName: 'Description', type: 'rich', sanitizeByDefault: true },
        { internalName: 'comments', prettyName: 'Comments', type: 'rich', sanitizeByDefault: true },
    ];

    // Fields shown in the detail header metadata grid
    let metaFields = [
        { internalName: 'entry_identifier', prettyName: 'Identifier', sanitizeByDefault: false },
        { internalName: 'start_date', prettyName: 'Start Date', toDisplay: v => formatDateFull(v), sanitizeByDefault: false },
        { internalName: 'end_date', prettyName: 'End Date', toDisplay: v => formatDateFull(v), sanitizeByDefault: false },
        { internalName: 'source_ip', prettyName: 'Source', mono: true, sanitizeByDefault: true },
        { internalName: 'dest_ip', prettyName: 'Destination', mono: true, sanitizeByDefault: true },
        { internalName: 'tool', prettyName: 'Tool', sanitizeByDefault: false },
        { internalName: 'user_context', prettyName: 'User Context', mono: true, sanitizeByDefault: true },
        { internalName: 'operator_name', prettyName: 'Operator', sanitizeByDefault: false },
    ];

    // --- Utility functions ---
    function formatDate(v) {
        if (!v) return '';
        return jsEscape(v).replace(/\.\d+/, '').replace('Z', '').replace('T', ' ').replace(/:\d\d$/, '');
    }

    function formatDateFull(v) {
        if (!v) return '';
        return jsEscape(v).replace(/\.\d+/, '').replace('Z', '').replace('T', ' ');
    }

    function truncateText(text, maxLen) {
        if (!text) return '';
        let str = String(text);
        return str.length > maxLen ? str.slice(0, maxLen) + '\u2026' : str;
    }

    function stylizeTags(tagString) {
        let tags = tagString.split(',');
        let tagHtml = '';
        for (const tag of tags) {
            if (tag === '') continue;
            let upper = tag.toUpperCase();
            if (upper.includes('ATT&AMP;CK') || upper.includes('ATTACK') || upper.includes('MITRE') || upper.includes('TTP')) {
                tagHtml += `<span class="badge badge-danger">${tag}</span>`;
            } else if (upper.includes('CREDS') || upper.includes('CREDENTIALS')) {
                tagHtml += `<span class="badge badge-warning">${tag}</span>`;
            } else if (upper.includes('VULN') || upper.includes('VULNERABILITY') || upper.includes('EXPLOIT')) {
                tagHtml += `<span class="badge badge-success">${tag}</span>`;
            } else if (upper.includes('DETECT') || upper.includes('DETECTION')) {
                tagHtml += `<span class="badge badge-info">${tag}</span>`;
            } else if (upper.includes('OBJECTIVE') || upper.includes('EVIDENCE')) {
                tagHtml += `<span class="badge badge-primary">${tag}</span>`;
            } else if (upper.includes('RECORDING')) {
                tagHtml += `<span class="badge badge-dark">${tag}</span>`;
            } else {
                tagHtml += `<span class="badge badge-secondary">${tag}</span>`;
            }
        }
        return tagHtml;
    }

    // --- Placeholders ---
    function updatePlaceholder() {
        if (pendingOperation) {
            $oplogTableLoading.show();
            $oplogTableNoEntries.hide();
            return;
        }
        $oplogTableLoading.hide();
        $oplogTableNoEntries.toggle($tableBody.find('> tr').length === 0);
    }

    // --- Column management ---
    function updateColumnInfo(extra_field_specs) {
        extra_field_specs.forEach(spec => {
            let toHtmlFunc;
            if (spec.type === 'checkbox') {
                toHtmlFunc = v => (v ? '<i class="fas fa-check"></i>' : '<i class="fas fa-times"></i>');
            } else if (spec.type === 'rich_text') {
                toHtmlFunc = v => v;
            } else {
                toHtmlFunc = jsEscape;
            }

            summaryColumns.push({
                checkBoxID: `extra-field-${jsEscape(spec.internal_name)}Checkbox`,
                columnClass: `extra-field-${jsEscape(spec.internal_name)}Column`,
                prettyName: jsEscape(spec.display_name),
                internalName: jsEscape(spec.internal_name),
                toHtml: toHtmlFunc,
                getValue: entry => entry.extra_fields[spec.internal_name],
            });
        });
    }

    function generateTableHeaders() {
        let out = '<tr>';
        summaryColumns.forEach((col, idx) => {
            out += `<th class="${col.columnClass} text-left none" data-sorter="text" data-col-index="${idx}" style="cursor:pointer;">${col.prettyName}</th>`;
        });
        out += '</tr>';
        return out;
    }

    function coupleCheckboxColumn(checkboxId, columnClass, col) {
        $(checkboxId).change(function () {
            if (!this.checked) {
                $(columnClass).hide();
                if (col.showByDefault === false) {
                    // Remove from explicit-show list; reverts to hidden-by-default
                    shownLogTblColumns = shownLogTblColumns.filter(v => v !== columnClass);
                } else {
                    // Add to hidden list; overrides shown-by-default
                    if (!hiddenLogTblColumns.includes(columnClass)) {
                        hiddenLogTblColumns.push(columnClass);
                    }
                }
            } else {
                $(columnClass).show();
                if (col.showByDefault === false) {
                    // Add to explicit-show list; overrides hidden-by-default
                    if (!shownLogTblColumns.includes(columnClass)) {
                        shownLogTblColumns.push(columnClass);
                    }
                } else {
                    // Remove from hidden list; reverts to shown-by-default
                    hiddenLogTblColumns = hiddenLogTblColumns.filter(v => v !== columnClass);
                }
            }
            localStorage.setItem('hiddenLogTblColumns', JSON.stringify(hiddenLogTblColumns));
            localStorage.setItem('shownLogTblColumns', JSON.stringify(shownLogTblColumns));
            $table.trigger('updateAll');
        });
    }

    function buildColumnsCheckboxes() {
        summaryColumns.forEach(col => {
            let cls = '.' + col.columnClass;
            let visible;
            if (col.showByDefault === false) {
                // Hidden by default; visible only if user explicitly enabled it
                visible = shownLogTblColumns.includes(cls);
            } else {
                // Shown by default; hidden only if user explicitly disabled it
                visible = !hiddenLogTblColumns.includes(cls);
            }
            let checked = visible ? 'checked' : '';
            let html = `
            <div class="form-check-inline">
              <div class="custom-control custom-switch">
                <input type="checkbox" id="${col.checkBoxID}" class="form-check-input custom-control-input" ${checked}/>
                <label class="form-check-label custom-control-label" for="${col.checkBoxID}">${col.prettyName}</label>
              </div>
            </div>`;
            $checkboxList.append(html);
            coupleCheckboxColumn('#' + col.checkBoxID, cls, col);
        });
    }

    function buildSanitizeCheckboxes() {
        let coveredNames = new Set();
        // Summary columns
        summaryColumns.forEach(col => {
            coveredNames.add(col.internalName);
            let checked = (col.sanitizeByDefault === undefined || col.sanitizeByDefault) ? 'checked' : '';
            $sanitizeCheckboxList.append(`
            <div class="form-check-inline">
              <div class="custom-control custom-switch">
                <input type="checkbox" name="${col.internalName}" id="sanitize_${col.checkBoxID}" class="form-check-input custom-control-input" ${checked}/>
                <label class="form-check-label custom-control-label" for="sanitize_${col.checkBoxID}">${col.prettyName}</label>
              </div>
            </div>`);
        });
        // Detail fields - skip any already added via summaryColumns
        detailFields.forEach(f => {
            if (coveredNames.has(f.internalName)) return;
            coveredNames.add(f.internalName);
            let checked = (f.sanitizeByDefault === undefined || f.sanitizeByDefault) ? 'checked' : '';
            $sanitizeCheckboxList.append(`
            <div class="form-check-inline">
              <div class="custom-control custom-switch">
                <input type="checkbox" name="${f.internalName}" id="sanitize_${f.internalName}Checkbox" class="form-check-input custom-control-input" ${checked}/>
                <label class="form-check-label custom-control-label" for="sanitize_${f.internalName}Checkbox">${f.prettyName}</label>
              </div>
            </div>`);
        });
        // Meta fields - skip any already covered
        metaFields.forEach(f => {
            if (coveredNames.has(f.internalName)) return;
            let checked = (f.sanitizeByDefault === undefined || f.sanitizeByDefault) ? 'checked' : '';
            $sanitizeCheckboxList.append(`
            <div class="form-check-inline">
              <div class="custom-control custom-switch">
                <input type="checkbox" name="${f.internalName}" id="sanitize_${f.internalName}Checkbox" class="form-check-input custom-control-input" ${checked}/>
                <label class="form-check-label custom-control-label" for="sanitize_${f.internalName}Checkbox">${f.prettyName}</label>
              </div>
            </div>`);
        });
    }

    function hideColumns() {
        summaryColumns.forEach(col => {
            let $cb = $('#' + col.checkBoxID);
            if (!$cb.prop('checked')) {
                $('.' + col.columnClass).hide();
            }
        });
    }

    // --- Row generation for left pane ---
    function generateRow(entry) {
        let safeId = sanitizeEntryId(entry.id);
        if (safeId === null) return '';
        entryDataStore[safeId] = entry;
        let out = `<tr id="entry-${safeId}" data-entry-id="${safeId}">`;
        summaryColumns.forEach(col => {
            let value = col.getValue ? col.getValue(entry) : entry[col.internalName];
            let toHtml = col.toHtml ?? jsEscape;
            out += `<td class="${col.columnClass} text-left">${toHtml(value)}</td>`;
        });
        out += '</tr>';
        return out;
    }

    // --- Detail viewer (right pane) ---
    function renderDetail(entry) {
        if (!entry) {
            $detailContent.hide();
            $detailEmpty.show();
            return;
        }

        let safeId = parseInt(entry.id, 10);
        let tags = entry.tags ? stylizeTags(jsEscape(entry.tags)) : '';

        // Header
        let html = `<div class="oplog-detail-header">`;
        html += `<div class="oplog-detail-header-row">`;
        html += `<span class="oplog-detail-operator">${jsEscape(entry.operator_name || 'Unknown')}</span>`;
        html += `<span class="oplog-detail-date">${formatDateFull(entry.start_date)}</span>`;
        if (entry.entry_identifier) {
            html += `<span class="oplog-detail-id">${jsEscape(entry.entry_identifier)}</span>`;
        }
        html += `<div class="oplog-detail-actions">
            <button class="btn btn-sm btn-outline-secondary" data-toggle="tooltip" title="Edit entry" onclick="editEntry(${safeId})"><i class="fas fa-edit"></i></button>
            <button class="btn btn-sm btn-outline-secondary" data-toggle="tooltip" title="Copy entry" onclick="copyEntry(this)" entry-id="${safeId}"><i class="fa fa-copy"></i></button>
            <button class="btn btn-sm btn-outline-secondary" data-toggle="tooltip" title="Copy as JSON" onclick="convertRowToJSON(${safeId})"><i class="fas fa-clipboard"></i></button>
            <button class="btn btn-sm btn-outline-secondary" data-toggle="tooltip" title="Copy deep link" onclick="copyDeepLink(${safeId})"><i class="fas fa-link"></i></button>
            <button class="btn btn-sm btn-outline-danger danger" data-toggle="tooltip" title="Delete entry" onclick="deleteEntry(this)" entry-id="${safeId}"><i class="fa fa-trash"></i></button>
            <button class="btn btn-sm btn-outline-secondary" data-toggle="tooltip" title="Close details (ESC)" onclick="deselectEntry()"><i class="fas fa-times"></i></button>
        </div>`;
        html += `</div>`;
        if (tags) {
            html += `<div class="oplog-detail-header-row"><div class="oplog-detail-tags">${tags}</div></div>`;
        }
        html += `</div>`;

        // Body
        html += `<div class="oplog-detail-body">`;

        // Metadata grid
        html += `<div class="oplog-meta-grid">`;
        metaFields.forEach(f => {
            let val = entry[f.internalName];
            if (!val || val.toString().trim() === '') return;
            let display = f.toDisplay ? f.toDisplay(val) : jsEscape(val);
            let monoClass = f.mono ? ' mono' : '';
            html += `<div class="oplog-meta-item">
                <span class="oplog-meta-label">${f.prettyName}</span>
                <span class="oplog-meta-value${monoClass}">${display}</span>
            </div>`;
        });
        html += `</div>`;

        // Detail sections (command, output, description, comments)
        detailFields.forEach(f => {
            let val = entry[f.internalName];
            if (!val || val.toString().trim() === '') return;

            html += `<div class="oplog-detail-section">`;
            html += `<div class="oplog-detail-label">${f.prettyName}
                <i class="fas fa-copy copy-btn" onclick="copyFieldToClipboard(${safeId}, '${f.internalName}')" title="Copy to clipboard"></i>
            </div>`;

            if (f.type === 'code') {
                html += `<pre class="oplog-code-block">${jsEscape(val)}</pre>`;
            } else {
                // Sanitize with DOMPurify before rendering as HTML (defense-in-depth
                // alongside server-side bleach sanitization on save).
                let safeVal = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(val) : jsEscape(val);
                html += `<div class="oplog-rich-content">${safeVal}</div>`;
            }
            html += `</div>`;
        });

        // Extra fields (if any)
        if (entry.extra_fields && oplog_entry_extra_fields_spec.length > 0) {
            oplog_entry_extra_fields_spec.forEach(spec => {
                let val = entry.extra_fields[spec.internal_name];
                if (val === undefined || val === null || val.toString().trim() === '') return;

                html += `<div class="oplog-detail-section">`;
                html += `<div class="oplog-detail-label">${jsEscape(spec.display_name)}</div>`;

                if (spec.type === 'checkbox') {
                    html += val ? '<i class="fas fa-check text-success"></i> Yes' : '<i class="fas fa-times text-danger"></i> No';
                } else if (spec.type === 'rich_text') {
                    let safeVal = (typeof DOMPurify !== 'undefined') ? DOMPurify.sanitize(val) : jsEscape(val);
                    html += `<div class="oplog-rich-content">${safeVal}</div>`;
                } else {
                    html += `<div class="oplog-rich-content">${jsEscape(val)}</div>`;
                }
                html += `</div>`;
            });
        }

        // --- Attachments: Screenshot & Terminal Recording ---

        // Evidence section
        let projectHasReports = $splitContainer.attr('data-project-has-reports') === 'true';
        html += `<div class="oplog-attachment-section">`;
        html += `<div class="oplog-attachment-label"><i class="fas fa-file-image"></i> Evidence</div>`;
        html += `<div id="evidence-list-${safeId}" class="oplog-evidence-list"></div>`;
        if (projectHasReports) {
            html += `<div class="oplog-attachment-dropzone" id="evidence-dropzone-${safeId}" onclick="uploadEvidence(${safeId})">
                <div class="dropzone-icon"><i class="fas fa-cloud-upload-alt"></i></div>
                <div class="dropzone-text">Drag & drop a file or click to upload evidence</div>
                <div class="dropzone-hint">Allowed: txt, md, log, jpg, jpeg, png</div>
            </div>`;
        } else {
            let projectUrl = jsEscape($splitContainer.attr('data-project-url') || '#');
            html += `<div class="alert alert-info mb-0 d-flex align-items-center" role="alert">
                <i class="fas fa-info-circle fa-lg flex-shrink-0 mr-3"></i>
                <p class="mb-0 text-left mb-0">No reports exist for this project. <a class="clickable" href="${projectUrl}#documents">Create a report</a> to upload evidence.</p>
            </div>`;
        }
        html += `</div>`;

        // Asciinema terminal recording section
        let hasRecordingUrl = !!entry.recording_url;

        html += `<div class="oplog-attachment-section">`;
        html += `<div class="oplog-attachment-label"><i class="fas fa-terminal"></i> Terminal Recording</div>`;
        if (hasRecordingUrl) {
            html += `<div class="oplog-asciinema-container" id="asciinema-player-${safeId}"></div>`;
            html += `<div class="oplog-asciinema-actions">
                <a href="${jsEscape(entry.recording_url)}" class="btn btn-sm btn-outline-primary" download>
                    <i class="fas fa-download"></i> Download Recording
                </a>
                <button class="btn btn-sm btn-outline-danger" onclick="removeRecording(${safeId})">
                    <i class="fas fa-times"></i> Remove Recording
                </button>
            </div>`;
        } else {
            html += `<div class="oplog-attachment-dropzone" id="recording-dropzone-${safeId}" onclick="uploadRecording(${safeId})">
                <div class="dropzone-icon"><i class="fas fa-play-circle"></i></div>
                <div class="dropzone-text">No terminal recording attached</div>
                <div class="dropzone-hint">Drag & drop a .cast or .cast.gz file or click to upload</div>
            </div>`;
        }
        html += `</div>`;

        html += `</div>`; // end body
        $detailContent.html(html).show();
        $detailEmpty.hide();
        $('[data-toggle="tooltip"]').tooltip();

        // Initialize asciinema player if recording data is available
        if (typeof AsciinemaPlayer !== 'undefined') {
            let playerEl = document.getElementById('asciinema-player-' + safeId);
            if (playerEl) {
                let playerOpts = { fit: 'width', theme: 'dracula', idleTimeLimit: 3, preload: true };
                if (hasRecordingUrl) {
                    AsciinemaPlayer.create(entry.recording_url, playerEl, playerOpts);
                }
            }
        }

        // Wire up drag-and-drop on all dropzones
        $detailContent.find('.oplog-attachment-dropzone').each(function () {
            let $dz = $(this);
            let dropzoneId = $dz.attr('id') || '';

            $dz.on('dragenter dragover', function (e) {
                e.preventDefault();
                e.stopPropagation();
                $dz.addClass('dragover');
            });
            $dz.on('dragleave', function (e) {
                e.preventDefault();
                e.stopPropagation();
                $dz.removeClass('dragover');
            });
            $dz.on('drop', function (e) {
                e.preventDefault();
                e.stopPropagation();
                $dz.removeClass('dragover');

                let files = e.originalEvent.dataTransfer.files;
                if (files.length === 0) return;
                let file = files[0];

                if (dropzoneId.startsWith('recording-dropzone')) {
                    let targetEntryId = parseInt(dropzoneId.replace('recording-dropzone-', ''));
                    uploadCastFile(file, targetEntryId);
                } else if (dropzoneId.startsWith('evidence-dropzone')) {
                    let targetEntryId = parseInt(dropzoneId.replace('evidence-dropzone-', ''));
                    openEvidenceUploadModal(targetEntryId, file);
                }
            });
        });

        // Fetch and render evidence list for this entry
        fetchAndRenderEvidenceList(safeId);
    }

    // Validate that a raw value is a positive integer; returns Number or null.
    function sanitizeEntryId(rawId) {
        let str = String(rawId);
        return /^[1-9][0-9]*$/.test(str) ? Number(str) : null;
    }

    function selectEntry(entryId) {
        let safeId = sanitizeEntryId(entryId);
        if (safeId === null) return;
        selectedEntryId = safeId;
        $tableBody.find('tr').removeClass('oplog-entry-selected');
        $(`#entry-${safeId}`).addClass('oplog-entry-selected');
        $splitContainer.addClass('oplog-has-selection');
        renderDetail(entryDataStore[safeId]);
    }

    function scrollToEntry(entryId) {
        let $row = $(`#entry-${entryId}`);
        if ($row.length === 0) return;
        $row[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
        $row.addClass('oplog-entry-highlight');
        setTimeout(function () { $row.removeClass('oplog-entry-highlight'); }, 2000);
    }

    function deselectEntry() {
        if (selectedEntryId !== null) {
            $tableBody.find('tr').removeClass('oplog-entry-selected');
            selectedEntryId = null;
            $splitContainer.removeClass('oplog-has-selection');
            renderDetail(null);
        }
    }

    // Expose deselectEntry globally for onclick handlers
    window.deselectEntry = deselectEntry;

    // --- Global actions ---
    window.createEntry = function (id) {
        socket.send(JSON.stringify({ action: 'create', oplog_id: id }));
        displayToastTop({ type: 'success', string: 'Successfully added a log entry.', title: 'Oplog Update' });
    };

    window.deleteEntry = function ($ele) {
        let id = $($ele).attr('entry-id');
        socket.send(JSON.stringify({ action: 'delete', oplogEntryId: id }));
        displayToastTop({ type: 'success', string: 'Successfully deleted a log entry.', title: 'Oplog Update' });
    };

    window.copyEntry = function ($ele) {
        let id = $($ele).attr('entry-id');
        socket.send(JSON.stringify({ action: 'copy', oplogEntryId: id }));
        displayToastTop({ type: 'success', string: 'Successfully cloned a log entry.', title: 'Oplog Update' });
    };

    window.editEntry = function (entryId) {
        let safeId = sanitizeEntryId(entryId);
        if (safeId === null) return;
        let url = window.location.origin + '/oplog/entry/update/' + safeId;
        $('.oplog-form-div').load(url, function () {
            $('#edit-modal').modal('toggle');
            tinymceLogInit();
            formAjaxSubmit('#oplog-entry-form', '#edit-modal');
        });
    };

    window.convertRowToJSON = function (entryId) {
        let entry = entryDataStore[entryId];
        if (!entry) return;

        let jsonObj = {};
        metaFields.forEach(f => { jsonObj[f.prettyName] = entry[f.internalName] || ''; });
        detailFields.forEach(f => { jsonObj[f.prettyName] = entry[f.internalName] || ''; });
        jsonObj['Tags'] = entry.tags || '';

        let json = JSON.stringify(jsonObj, null, 2);
        if (navigator.clipboard) {
            navigator.clipboard.writeText(json).then(function () {
                displayToastTop({ type: 'success', string: 'Copied entry to clipboard as JSON.', title: 'Copied' });
            });
        } else {
            let $temp = $('<textarea>');
            $('body').append($temp);
            $temp.val(json).select();
            document.execCommand('copy');
            $temp.remove();
        }
    };

    window.copyDeepLink = function (entryId) {
        let url = window.location.origin + window.location.pathname + '?entry=' + entryId + '#entry-' + entryId;
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(function () {
                displayToastTop({ type: 'success', string: 'Copied deep link to clipboard.', title: 'Copied' });
            });
        } else {
            let $temp = $('<textarea>');
            $('body').append($temp);
            $temp.val(url).select();
            document.execCommand('copy');
            $temp.remove();
        }
    };

    // --- Attachment functions ---

    // Upload a .cast or .cast.gz file to the server for persistent storage, then update the detail view
    function uploadCastFile(file, entryId) {
        // Skip client-side content validation for gzipped files (server will validate)
        let isGzipped = file.name.toLowerCase().endsWith('.gz');

        if (isGzipped) {
            // For gzipped files, skip JSON validation and proceed directly to upload
            uploadCastFileToServer(file, entryId);
            return;
        }

        // Basic client-side validation before sending (only for non-gzipped files)
        let reader = new FileReader();
        reader.onload = function (ev) {
            let castData = ev.target.result;
            try {
                let firstLine = castData.split('\n')[0];
                let header = JSON.parse(firstLine);
                if (!header.version && !header.width) {
                    displayToastTop({ type: 'warning', string: 'This file does not appear to be a valid asciicast recording.', title: 'Invalid File' });
                    return;
                }
            } catch (e) {
                displayToastTop({ type: 'warning', string: 'Could not parse file. Please select a valid .cast file.', title: 'Invalid File' });
                return;
            }
            uploadCastFileToServer(file, entryId);
        };
        reader.onerror = function () {
            displayToastTop({ type: 'error', string: 'Failed to read file.', title: 'File Error' });
        };
        reader.readAsText(file);
    }

    // Helper function to upload the file to the server
    function uploadCastFileToServer(file, entryId) {

        let $dropzone = $(`#recording-dropzone-${entryId}`);
        $dropzone.html('<div class="dropzone-icon"><i class="fas fa-sync fa-spin"></i></div><div class="dropzone-text">Uploading...</div>');

        let formData = new FormData();
        formData.append('recording_file', file);
        let csrfToken = $splitContainer.attr('data-csrf-token');

        window.fetch('/oplog/entry/' + entryId + '/recording/upload', {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': csrfToken },
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.result === 'success') {
                if (entryDataStore[entryId]) {
                    entryDataStore[entryId].recording_url = data.recording_url;
                }
                if (selectedEntryId == entryId) {
                    renderDetail(entryDataStore[entryId]);
                }
                displayToastTop({ type: 'success', string: 'Terminal recording uploaded successfully.', title: 'Recording Saved' });
                if (data.warning) {
                    displayToastTop({ type: 'warning', string: data.warning, title: 'Recording Warning' });
                }
            } else {
                displayToastTop({ type: 'error', string: data.message || 'Upload failed.', title: 'Upload Error' });
                if (selectedEntryId == entryId) {
                    renderDetail(entryDataStore[entryId]);
                }
            }
        })
        .catch(function () {
            displayToastTop({ type: 'error', string: 'Network error during upload.', title: 'Upload Error' });
            if (selectedEntryId == entryId) {
                renderDetail(entryDataStore[entryId]);
            }
        });
    }

    window.uploadEvidence = function (entryId) {
        let $input = $('<input type="file" accept=".txt,.md,.log,.jpg,.jpeg,.png" style="display:none;">');
        $input.on('change', function (e) {
            let file = e.target.files[0];
            if (file) openEvidenceUploadModal(entryId, file);
            $input.remove();
        });
        $('body').append($input);
        $input.click();
    };

    function getEvidenceUploadUrl(entryId) {
        let baseUrl = $splitContainer.attr('data-evidence-upload-base-url');
        return baseUrl + entryId + '/evidence/upload';
    }

    function showPendingFileIndicator(modalSelector, formSelector, file) {
        let $fileInput = $(formSelector + ' #id_document');
        // Update the Bootstrap 4 custom-file-label to show the filename in-place of "---"
        let $label = $fileInput.next('label.custom-file-label');
        if ($label.length) {
            $label.text(file.name);
        }
        // When user picks a file manually, the pre-loaded file is no longer needed
        $fileInput.off('change.evidencePending').on('change.evidencePending', function () {
            if (this.files.length > 0) {
                $(modalSelector).removeData('pending-file');
                $label.text(this.files[0].name);
            }
        });
    }

    function openEvidenceUploadModal(entryId, file) {
        let url = getEvidenceUploadUrl(entryId);
        let csrfToken = $splitContainer.attr('data-csrf-token');
        let $modal = $('#evidence-modal');
        let $formDiv = $modal.find('.oplog-evidence-form-div');

        // Store the file on the modal so submit can access it without DataTransfer injection.
        // DataTransfer sets input.files but browsers don't update the native UI text, and
        // re-selecting the same file from Browse won't fire a change event.
        $modal.data('pending-file', file);

        $formDiv.html('<div class="text-center p-4"><i class="fa fa-sync fa-spin"></i> Loading form...</div>');
        $modal.modal('show');

        $formDiv.load(url, function () {
            // Pre-populate the friendly name from the file name
            let friendlyName = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
            $('#id_friendly_name').val(friendlyName);

            // Show a visible indicator and wire up manual-selection clearing
            showPendingFileIndicator('#evidence-modal', '#oplog-evidence-form', file);

            evidenceFormAjaxSubmit('#oplog-evidence-form', '#evidence-modal', entryId, csrfToken);
        });
    }

    function evidenceFormAjaxSubmit(formSelector, modalSelector, entryId, csrfToken) {
        $(formSelector).off('submit').on('submit', function (e) {
            e.preventDefault();
            let formEl = this;
            let formData = new FormData(formEl);

            // If the user didn't manually pick a file, append the pre-loaded one
            let fileInput = formEl.querySelector('#id_document');
            if (fileInput && fileInput.files.length === 0) {
                let pendingFile = $(modalSelector).data('pending-file');
                if (pendingFile) {
                    formData.append('document', pendingFile, pendingFile.name);
                }
            }

            $.ajax({
                type: 'POST',
                url: $(formEl).attr('action'),
                data: formData,
                processData: false,
                contentType: false,
                headers: { 'X-CSRFToken': csrfToken },
                success: function (response) {
                    if (typeof response === 'object' && response.result === 'success') {
                        $(modalSelector).modal('hide');
                        displayToastTop({ type: 'success', string: 'Evidence uploaded successfully.', title: 'Evidence' });
                        fetchAndRenderEvidenceList(entryId);
                    } else {
                        // Server returned form HTML with errors
                        $(modalSelector).find('.oplog-evidence-form-div').html(response);
                        evidenceFormAjaxSubmit(formSelector, modalSelector, entryId, csrfToken);
                        // Re-show the indicator if a file is still pending
                        let pf = $(modalSelector).data('pending-file');
                        if (pf) showPendingFileIndicator(modalSelector, formSelector, pf);
                    }
                },
                error: function (xhr) {
                    displayToastTop({ type: 'error', string: 'Failed to upload evidence. Please try again.', title: 'Error' });
                },
            });
        });
    }

    function fetchAndRenderEvidenceList(entryId) {
        let baseUrl = $splitContainer.attr('data-evidence-upload-base-url');
        let listUrl = baseUrl + entryId + '/evidence/list';
        let $list = $(`#evidence-list-${entryId}`);
        if ($list.length === 0) return;

        $.getJSON(listUrl, function (data) {
            if (data.result !== 'success') return;
            let items = data.evidence || [];
            if (items.length === 0) {
                $list.html('');
                return;
            }
            // Text evidence first, then images; alphabetical within each group
            items.sort(function (a, b) {
                let aIsImage = /\.(jpg|jpeg|png)$/i.test(a.filename) ? 1 : 0;
                let bIsImage = /\.(jpg|jpeg|png)$/i.test(b.filename) ? 1 : 0;
                if (aIsImage !== bIsImage) return aIsImage - bIsImage;
                return a.friendly_name.localeCompare(b.friendly_name);
            });
            let html = '<div class="oplog-evidence-items mb-3">';
            items.forEach(function (ev) {
                let isImage = /\.(jpg|jpeg|png)$/i.test(ev.filename);
                let icon = isImage ? 'fa-image' : 'fa-file-alt';
                let preview = '';
                if (isImage && ev.document_url) {
                    preview = `<img src="${jsEscape('/reporting/evidence/download/' + ev.id)}" alt="${jsEscape(ev.friendly_name)}" class="oplog-evidence-thumb text-center" onclick="openLightbox('${jsEscape('/reporting/evidence/download/' + ev.id)}')" loading="lazy">`;
                }
                let detailUrl = window.location.origin + '/reporting/reports/evidence/' + ev.id;
                html += `<div class="oplog-evidence-item text-left mt-2">
                    <div class="oplog-evidence-item-header">
                        <i class="fas ${icon}"></i>
                        <a href="${jsEscape(detailUrl)}" target="_blank" title="View">${jsEscape(ev.friendly_name)} (${jsEscape(ev.uploaded_by_user)})</a>
                    </div>
                    ${preview}
                </div>`;
            });
            html += '</div>';
            $list.html(html);
        });
    }

    window.uploadRecording = function (entryId) {
        let $input = $('<input type="file" accept=".cast,.gz,.txt,.json" style="display:none;">');
        $input.on('change', function (e) {
            let file = e.target.files[0];
            if (file) uploadCastFile(file, entryId);
            $input.remove();
        });
        $('body').append($input);
        $input.click();
    };

    window.removeRecording = function (entryId) {
        let csrfToken = $splitContainer.attr('data-csrf-token');
        window.fetch('/oplog/entry/' + entryId + '/recording/delete', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.result === 'success') {
                if (entryDataStore[entryId]) {
                    entryDataStore[entryId].recording_url = null;
                }
                if (selectedEntryId == entryId) {
                    renderDetail(entryDataStore[entryId]);
                }
                displayToastTop({ type: 'info', string: 'Recording removed.', title: 'Recording Deleted' });
            } else {
                displayToastTop({ type: 'error', string: data.message || 'Delete failed.', title: 'Error' });
            }
        })
        .catch(function () {
            displayToastTop({ type: 'error', string: 'Network error.', title: 'Error' });
        });
    };

    window.openLightbox = function (url) {
        let $lb = $(`<div class="oplog-lightbox">
            <span class="oplog-lightbox-close"><i class="fas fa-times"></i></span>
            <img src="${url}" alt="Screenshot">
        </div>`);
        $lb.click(function () { $(this).fadeOut(150, function () { $(this).remove(); }); });
        $(document).one('keydown.lightbox', function (e) {
            if (e.keyCode === 27) { $lb.fadeOut(150, function () { $(this).remove(); }); }
        });
        $('body').append($lb);
    };

    window.copyFieldToClipboard = function (entryId, fieldName) {
        let entry = entryDataStore[entryId];
        if (!entry) return;
        let val = entry[fieldName] || '';
        if (navigator.clipboard) {
            navigator.clipboard.writeText(val).then(function () {
                displayToastTop({ type: 'success', string: 'Copied to clipboard.', title: 'Copied' });
            });
        } else {
            let $temp = $('<textarea>');
            $('body').append($temp);
            $temp.val(val).select();
            document.execCommand('copy');
            $temp.remove();
        }
    };

    // --- WebSocket ---
    function fetch(clear_existing) {
        const new_filter = $searchInput.val();
        const new_offset = clear_existing ? 0 : $tableBody.find('> tr').length;
        if (pendingOperation !== null && pendingOperation.filter === new_filter && pendingOperation.offset === new_offset) return;

        pendingOperation = { filter: new_filter, offset: new_offset };
        allEntriesFetched = false;

        if (clear_existing) {
            $tableBody.find('tr').remove();
            entryDataStore = {};
            if (selectedEntryId) {
                selectedEntryId = null;
                $detailContent.hide();
                $detailEmpty.show();
            }
        }
        $oplogTableNoEntries.hide();
        $oplogTableLoading.show();

        socket.send(JSON.stringify({
            action: 'sync',
            oplog_id: oplog_id,
            offset: new_offset,
            filter: new_filter,
        }));
    }

    function connect() {
        let endpoint = protocol + window.location.host + '/ws' + window.location.pathname;
        socket = new WebSocket(endpoint);

        socket.onopen = function () {
            $connectionStatus.html('Connected');
            $connectionStatus.removeClass('disconnected').addClass('connected');
            errorDisplayed = false;
            $oplogTableLoading.show();
            fetch(true);
        };

        socket.onmessage = function (e) {
            let message = JSON.parse(e.data);

            if (message.action === 'sync') {
                if (!pendingOperation || pendingOperation.filter !== message.filter || pendingOperation.offset !== message.offset) return;
                pendingOperation = null;

                let entries = message.data;
                if (entries.length !== 0) {
                    entries.forEach(el => $tableBody.append(generateRow(el)));
                } else {
                    allEntriesFetched = true;
                }
                updatePlaceholder();
                hideColumns();
                $oplogTableLoading.hide();
                $table.trigger('updateAll');
                $table.trigger('updateCache');

                // Deep-link: scroll to and select the target entry if it's now loaded
                if (deepLinkEntryId && !deepLinkResolved) {
                    if (entryDataStore[deepLinkEntryId]) {
                        // Entry arrived in this page — select and scroll
                        deepLinkResolved = true;
                        selectEntry(deepLinkEntryId);
                        scrollToEntry(deepLinkEntryId);
                    } else if (allEntriesFetched) {
                        // All pages exhausted and entry still not found — fall back to detail-pane display
                        deepLinkResolved = true;
                        socket.send(JSON.stringify({ action: 'fetch_entry', oplogEntryId: deepLinkEntryId }));
                    } else {
                        // Entry not yet in this page — load the next page and keep checking
                        fetch(false);
                    }
                } else if (!deepLinkEntryId && !selectedEntryId && $tableBody.find('tr').length > 0) {
                    // No deep-link: auto-select the first entry
                    let firstId = $tableBody.find('tr').first().data('entry-id');
                    selectEntry(firstId);
                }
            } else if (message.action === 'create') {
                if ($searchInput.val() !== '') {
                    fetch(true);
                    return;
                }

                let entry = message.data;
                let entryId = entry.id;
                entryDataStore[entryId] = entry;

                let $existing = $(`#entry-${entryId}`);
                if ($existing.length > 0) {
                    // Update existing row
                    let newHtml = generateRow(entry);
                    $existing.replaceWith(newHtml);
                    hideColumns();
                    $table.trigger('update');
                    // If this is the selected entry, re-render detail
                    if (selectedEntryId === entryId) {
                        renderDetail(entry);
                    }
                } else {
                    // New entry: prepend to DOM first, then rebuild the tablesorter
                    // cache from DOM order so the row stays at the top when no sort
                    // is active. Using addRows with resort=true causes tablesorter to
                    // sort by its internal cache order (new row appended last = bottom).
                    let $newRow = $(generateRow(entry)).prependTo($tableBody);
                    $newRow.hide();
                    hideColumns();
                    $table.trigger('update', [true]);
                    $newRow.fadeIn(400);
                }
                updatePlaceholder();
            } else if (message.action === 'fetch_entry') {
                // Deep-link: entry fetched for detail pane display.
                // The entry is not in the paginated DOM table, so we can only show
                // it in the detail pane. Show a toast so the user knows it loaded.
                let entry = message.data;
                entryDataStore[entry.id] = entry;
                selectEntry(entry.id);
                displayToastTop({
                    type: 'info',
                    title: 'Entry Loaded',
                    string: `Entry #${entry.id} was not found in the log table (it may be filtered or removed). Details are shown in the right pane.`,
                });
            } else if (message.action === 'delete') {
                let id = message.data;
                let $row = $(`#entry-${id}`);
                if ($row.length) {
                    $row.fadeOut(300, function () {
                        $(this).remove();
                        delete entryDataStore[id];
                        if (selectedEntryId == id) {
                            selectedEntryId = null;
                            $detailContent.hide();
                            $detailEmpty.show();
                        }
                        updatePlaceholder();
                    });
                }
                $table.trigger('updateAll');
            }
        };

        socket.onerror = function (e) {
            $connectionStatus.html('Disconnected');
            $connectionStatus.removeClass('connected').addClass('disconnected');
            console.error('[!] error: ', e);
            socket.close();
            if (!errorDisplayed) {
                displayToastTop({ type: 'error', string: 'Websocket has been disconnected.', title: 'Websocket Disconnected' });
                errorDisplayed = true;
            }
        };

        socket.onclose = function () {
            $connectionStatus.html('Disconnected');
            $connectionStatus.removeClass('connected').addClass('disconnected');
            if (!errorDisplayed) {
                displayToastTop({ type: 'error', string: 'Websocket has been disconnected.', title: 'Websocket Disconnected' });
                errorDisplayed = true;
            }
            setTimeout(function () {
                console.log('Retrying connection');
                connect();
            }, 5000);
        };
    }

    // --- Paste-to-upload: capture screenshot pastes and open the evidence upload modal ---
    $(window).on('paste', function (e) {
        let clipboard = e.originalEvent.clipboardData || e.clipboardData;
        if (!clipboard || !clipboard.files || clipboard.files.length === 0) return;

        let file = clipboard.files[0];
        if (!file.type.startsWith('image/')) return;

        // Give the pasted file a timestamped name if the browser provides a generic one
        let name = file.name && file.name !== 'image.png' ? file.name : 'screenshot-' + Date.now() + '.png';
        if (file.name !== name) {
            file = new File([file], name, { type: file.type });
        }

        let $modal = $('#evidence-modal');
        let modalOpen = $modal.is(':visible');

        if (modalOpen) {
            // Modal is already open — swap in the pasted file as the pending file
            $modal.data('pending-file', file);
            showPendingFileIndicator('#evidence-modal', '#oplog-evidence-form', file);
        } else if ($splitContainer.attr('data-project-has-reports') !== 'true') {
            // No reports on this project — let the alert in the detail pane guide the user
            let projectUrl = $splitContainer.attr('data-project-url') || '#';
            displayToastTop({ type: 'warning', string: 'No reports exist for this project. Create a report before uploading evidence.', title: 'No Reports', url: projectUrl });
        } else if (selectedEntryId) {
            // Open the modal for the currently-selected entry
            openEvidenceUploadModal(selectedEntryId, file);
        } else {
            displayToastTop({ type: 'warning', string: 'Select a log entry first, then paste to attach a screenshot.', title: 'No Entry Selected' });
        }
    });

    // --- Initialization ---
    connect();
    updateColumnInfo(oplog_entry_extra_fields_spec);
    buildColumnsCheckboxes();
    let headerHtml = generateTableHeaders();
    $tableHeader.html(headerHtml);
    $tableHeaderHidden.html(headerHtml);
    buildSanitizeCheckboxes();

    $table.tablesorter({
        cssAsc: 'down',
        cssDesc: 'up',
        cssNone: 'none',
        widgets: ['saveSort'],
        widgetOptions: { saveSort: true, storage_page: 'logDetailTable' },
    });

    // Sync sort-indicator classes from the hidden thead to the visible header
    function syncSortIndicators() {
        let $hiddenThs = $tableHeaderHidden.find('th');
        let $visibleThs = $tableHeader.find('th');
        $visibleThs.each(function (i) {
            let $vis = $(this);
            let $hid = $hiddenThs.eq(i);
            $vis.removeClass('up down none');
            if ($hid.hasClass('up')) $vis.addClass('up');
            else if ($hid.hasClass('down')) $vis.addClass('down');
            else $vis.addClass('none');
        });
    }

    // Handle clicks on visible header: compute sortList directly and trigger sorton
    $tableHeader.on('click', 'th', function (e) {
        let colIndex = $(this).data('col-index');
        if (colIndex === undefined) return;

        let currentSortList = $table[0].config.sortList || [];
        let existing = currentSortList.filter(function (s) { return s[0] === colIndex; })[0];
        // Toggle direction if already sorting by this column, else default to ascending (0)
        let newOrder = existing ? (existing[1] === 0 ? 1 : 0) : 0;

        let newSortList;
        if (e.shiftKey) {
            // Multi-sort: replace this column's entry or append it
            newSortList = currentSortList.filter(function (s) { return s[0] !== colIndex; });
            newSortList.push([colIndex, newOrder]);
        } else {
            newSortList = [[colIndex, newOrder]];
        }

        $table.trigger('sorton', [newSortList]);
    });

    // After every sort, copy indicators to visible header
    $table.on('sortEnd', function () {
        syncSortIndicators();
    });

    $('#resetSortBtn').click(function () {
        // If no sort is active, there is nothing to reset
        if (!$table[0].config.sortList.length) return false;
        // Clear saved sort from localStorage
        $table.trigger('saveSortReset');
        // Reorder rows by start_date descending (newest first), entry ID as tiebreaker
        let $rows = $tableBody.find('tr').detach();
        $rows.sort(function (a, b) {
            let idA = parseInt(a.dataset.entryId);
            let idB = parseInt(b.dataset.entryId);
            let dateA = (entryDataStore[idA] || {}).start_date || '';
            let dateB = (entryDataStore[idB] || {}).start_date || '';
            if (dateB > dateA) return 1;
            if (dateB < dateA) return -1;
            return idB - idA;
        });
        $tableBody.append($rows);
        // Clear active sort list, then re-index so tablesorter treats this as natural order
        $table[0].config.sortList = [];
        $table.trigger('updateAll');
        syncSortIndicators();
        return false;
    });

    $('#columnSelectDropdown').click(function () {
        $('#columnSelect').slideToggle('slow');
        $(this).toggleClass('open');
    });

    // --- Click handlers ---
    let clickTimer = null;
    let clickedEntryId = null;

    $tableBody.on('click', 'tr', function (e) {
        let entryId = $(this).data('entry-id');
        if (!entryId) return;

        if (clickTimer !== null && clickedEntryId === entryId) {
            // Double-click: open edit modal
            clearTimeout(clickTimer);
            clickTimer = null;
            clickedEntryId = null;
            editEntry(entryId);
        } else {
            // Single-click: select entry
            clickedEntryId = entryId;
            if (clickTimer) clearTimeout(clickTimer);
            clickTimer = setTimeout(function () {
                clickTimer = null;
                clickedEntryId = null;
                selectEntry(entryId);
            }, 220);
        }
    });

    // Infinite scroll
    $listScroll.scroll(function () {
        if (pendingOperation === null) {
            if ($(this).scrollTop() + $(this).innerHeight() + 1 >= $(this)[0].scrollHeight) {
                if (!allEntriesFetched) fetch(false);
            }
        }
    });

    // --- Resize handle ---
    let isResizing = false;
    let startX, startWidth;
    const $resizeHandle = $('#oplogResizeHandle');

    $resizeHandle.on('mousedown', function (e) {
        isResizing = true;
        startX = e.clientX;
        startWidth = $listPane.width();
        $resizeHandle.addClass('dragging');
        $('body').css('cursor', 'col-resize');
        $('body').css('user-select', 'none');
        e.preventDefault();
    });

    $(document).on('mousemove', function (e) {
        if (!isResizing) return;
        let newWidth = startWidth + (e.clientX - startX);
        let containerWidth = $splitContainer.width();
        let minLeft = 280;
        let minRight = 300;
        newWidth = Math.max(minLeft, Math.min(newWidth, containerWidth - minRight));
        $listPane.css('width', newWidth + 'px');
    });

    $(document).on('mouseup', function () {
        if (isResizing) {
            isResizing = false;
            $resizeHandle.removeClass('dragging');
            $('body').css('cursor', '');
            $('body').css('user-select', '');
        }
    });

    // --- AJAX form submit ---
    let formAjaxSubmit = function (form, modal) {
        $(form).submit(function (e) {
            e.preventDefault();
            $.ajax({
                type: $(this).attr('method'),
                url: $(this).attr('action'),
                data: $(this).serialize(),
                success: function (xhr) {
                    if ($(xhr).find('.has-error').length > 0) {
                        $(modal).find('.oplog-form-div').html(xhr);
                        formAjaxSubmit(form, modal);
                    } else {
                        $(modal).modal('toggle');
                    }
                    tinymceRemove();
                },
                error: function () {},
            });
        });
    };

    $('#edit-modal').on('hide.bs.modal', function () {
        tinymceRemove();
    });

    $('#evidence-modal').on('hide.bs.modal', function () {
        $(this).find('.oplog-evidence-form-div').html('');
        $(this).removeData('pending-file');
    });

    // --- Export ---
    $('#exportEntries').click(function () {
        let filename = generateDownloadName(oplog_name + '-log-export-' + oplog_id.toString() + '.csv');
        let export_url = $splitContainer.attr('data-oplog-export-url');
        download(export_url, filename);
    });

    // --- Search ---
    let filter_debounce_timeout_id = null;
    $searchInput.on('keyup', function (ev) {
        if (filter_debounce_timeout_id !== null) clearTimeout(filter_debounce_timeout_id);
        filter_debounce_timeout_id = setTimeout(function () {
            filter_debounce_timeout_id = null;
            fetch(true);
        }, ev.key === 'Enter' ? 0 : 500);
    });

    $clearSearchBtn.click(function () {
        $searchInput.val('');
        fetch(true);
    });

    // --- Mute toggle ---
    $('.js-toggle-mute').click(function () {
        let $toggleLink = $(this);
        let url = $(this).attr('toggle-mute-url');
        let oplogId = $(this).attr('toggle-mute-id');
        let csrftoken = $(this).attr('toggle-mute-csrftoken');
        $.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader('X-CSRFToken', csrftoken);
                }
            },
        });
        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
            data: { oplog: oplogId },
            success: function (data) {
                if (data.toggle) {
                    $toggleLink.removeClass('notification-bell-icon').addClass('silenced-notification-icon').text('Notifications: Off');
                } else {
                    $toggleLink.removeClass('silenced-notification-icon').addClass('notification-bell-icon').text('Notifications: On');
                }
                if (data.message) {
                    displayToastTop({ type: data.result, string: data.message, title: 'Log Update' });
                }
            },
        });
    });

    // --- Keyboard shortcuts ---
    $(window).keydown(function (event) {
        if (event.ctrlKey && event.keyCode === 78) {
            event.preventDefault();
            createEntry(oplog_id);
        }
        if (event.ctrlKey && event.keyCode === 83) {
            event.preventDefault();
            let filename = generateDownloadName(oplog_name + '-log-export-' + oplog_id.toString() + '.csv');
            let export_url = $splitContainer.attr('data-oplog-export-url');
            download(export_url, filename);
        }
    });

    // --- Arrow key navigation in list ---
    $(document).keydown(function (e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        // ESC key: deselect entry
        if (e.keyCode === 27) {
            e.preventDefault();
            deselectEntry();
            return;
        }
        
        if (!selectedEntryId) return;

        let $current = $(`#entry-${selectedEntryId}`);
        let $next = null;

        if (e.keyCode === 40) { // Down
            e.preventDefault();
            $next = $current.next('tr');
        } else if (e.keyCode === 38) { // Up
            e.preventDefault();
            $next = $current.prev('tr');
        } else if (e.keyCode === 13) { // Enter
            e.preventDefault();
            editEntry(selectedEntryId);
            return;
        }

        if ($next && $next.length > 0) {
            let nextId = $next.data('entry-id');
            if (nextId) {
                selectEntry(nextId);
                // Scroll into view
                let scrollContainer = $listScroll[0];
                let rowEl = $next[0];
                if (rowEl.offsetTop < scrollContainer.scrollTop) {
                    scrollContainer.scrollTop = rowEl.offsetTop;
                } else if (rowEl.offsetTop + rowEl.offsetHeight > scrollContainer.scrollTop + scrollContainer.clientHeight) {
                    scrollContainer.scrollTop = rowEl.offsetTop + rowEl.offsetHeight - scrollContainer.clientHeight;
                }
            }
        }
    });
});
