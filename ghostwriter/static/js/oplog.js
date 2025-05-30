/* JavaScript specific to the log entry view page goes here. */
$(document).ready(function() {
    const $table = $('#oplogTable');
    const $tableBody = $('#oplogTableBody');

    // Get the array of hidden columns from local storage or set to empty array
    let hiddenLogTblColumns = JSON.parse((localStorage.getItem('hiddenLogTblColumns') !== null ? localStorage.getItem('hiddenLogTblColumns') : JSON.stringify([])));

    // Assemble the array of column information for the table
    let columnInfo = [
        {
            checkBoxID: 'identifierCheckBox',
            columnClass: 'identifierColumn',
            prettyName: 'Identifier',
            internalName: 'entry_identifier',
            showByDefault: false,
            sanitizeByDefault: false
        },
        {
            checkBoxID: 'startDateCheckBox',
            columnClass: 'startDateColumn',
            prettyName: 'Start Date',
            internalName: 'start_date',
            toHtml: entry => jsEscape(entry).replace(/\.\d+/, "").replace("Z", "").replace("T", " "),
            sanitizeByDefault: false
        },
        {
            checkBoxID: 'endDateCheckbox',
            columnClass: 'endDateColumn',
            prettyName: 'End Date',
            internalName: 'end_date',
            toHtml: entry => jsEscape(entry).replace(/\.\d+/, "").replace("Z", "").replace("T", " "),
            sanitizeByDefault: false
        },
        {
            checkBoxID: 'sourceIPCheckbox',
            columnClass: 'sourceIPColumn',
            prettyName: 'Source',
            internalName: 'source_ip',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'destIPCheckbox',
            columnClass: 'destIPColumn',
            prettyName: 'Destination',
            internalName: 'dest_ip',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'toolNameCheckbox',
            columnClass: 'toolNameColumn',
            prettyName: 'Tool Name',
            internalName: 'tool',
            sanitizeByDefault: false
        },
        {
            checkBoxID: 'userContextCheckbox',
            columnClass: 'userContextColumn',
            prettyName: 'User Context',
            internalName: 'user_context',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'commandCheckbox',
            columnClass: 'commandColumn',
            prettyName: 'Command',
            internalName: 'command',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'descriptionCheckbox',
            columnClass: 'descriptionColumn',
            prettyName: 'Description',
            internalName: 'description',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'outputCheckbox',
            columnClass: 'outputColumn',
            prettyName: 'Output',
            internalName: 'output',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'commentsCheckbox',
            columnClass: 'commentsColumn',
            prettyName: 'Comments',
            internalName: 'comments',
            sanitizeByDefault: true
        },
        {
            checkBoxID: 'operatorCheckbox',
            columnClass: 'operatorColumn',
            prettyName: 'Operator',
            internalName: 'operator_name',
            sanitizeByDefault: false
        },
        {
            checkBoxID: 'tagsCheckbox',
            columnClass: 'tagsColumn',
            prettyName: 'Tags',
            internalName: 'tags',
            toHtml: entry => stylizeTags(jsEscape(entry)),
            sanitizeByDefault: false
        },
    ];

    const oplog_entry_extra_fields_spec = JSON.parse(document.getElementById('oplog_entry_extra_fields_spec').textContent);

    const oplog_name = $tableBody.attr("data-oplog-name");
    const oplog_id = parseInt($tableBody.attr("data-oplog-id"));
    const $tableHeader = $('#oplogTableHeader');
    const $checkboxList = $('#checkboxList');
    const $connectionStatus = $('#connectionStatus');
    const $sanitizeCheckboxList = $('#sanitize-checklist-form');
    const $searchInput = $('#searchInput');
    const $oplogTableNoEntries = $('#oplogTableNoEntries');
    const $oplogTableLoading = $('#oplogTableLoading');
    const $clearSearchBtn = $('#clearSearchBtn');

    let socket = null;
    let allEntriesFetched = false;
    let errorDisplayed = false;

    // null | {filter: string, offset: number}
    let pendingOperation = null;

    function updatePlaceholder() {
        if (pendingOperation) {
            $oplogTableLoading.show();
            $oplogTableNoEntries.hide();
            return;
        }

        $oplogTableLoading.hide();
        $oplogTableNoEntries.toggle($tableBody.find("> tr").length === 0)
    }

    $clearSearchBtn.click(function () {
        $searchInput.val("");
        fetch(true);
    });

    // Update `columnInfo` with extra fields
    function updateColumnInfo(extra_field_specs) {
        extra_field_specs.forEach(spec => {
            let toHtmlFunc;
            if (spec.type === "checkbox") {
                toHtmlFunc = v => v ? `<i class="fas fa-check"></i>` : `<i class="fas fa-times"></i>`;
            } else if (spec.type === "rich_text") {
                // Already XSS cleaned by backend
                toHtmlFunc = v => v;
            } else {
                toHtmlFunc = jsEscape;
            }

            columnInfo.push({
                checkBoxID: `extra-field-${jsEscape(spec.internal_name)}Checkbox`,
                columnClass: `extra-field-${jsEscape(spec.internal_name)}Column`,
                prettyName: jsEscape(spec.display_name),
                internalName: jsEscape(spec.internal_name),
                toHtml: toHtmlFunc,
                getValue: entry => entry.extra_fields[spec.internal_name],
            });
        });

        $oplogTableNoEntries.find("td").attr("colspan", columnInfo.length+1);
        $oplogTableLoading.find("td").attr("colspan", columnInfo.length+1);
    }

    // Generate table headers
    function generateTableHeaders() {
        let out = "<tr>";
        columnInfo.forEach(column => {
            out += `<th class="${column.columnClass} align-middle" data-sorter="text">${column.prettyName}</th>\n`
        });
        out += `<th class="optionsColumn align-middle" data-sorter="false">Options</th></tr>`;
        return out;
    }

    // Convert a table row to JSON and copy it to the clipboard
    window.convertRowToJSON = function (row_id) {
        let $row = document.getElementById(row_id);
        let header = [];
        let rows = [];

        $('#oplogTable > thead > th').each(function () {
            header.push($(this).text())
        })

        for (let j = 0; j < $row.cells.length - 1; j++) {
            $row[header[j]] = $row.cells[j].innerText;
        }
        rows.push($row);

        // Convert the array of row values to JSON
        let rawJson = JSON.stringify(rows[0])
        let jsonObj = JSON.parse(rawJson)
        delete jsonObj["Identifier"]
        let json = JSON.stringify(jsonObj, null, 2)

        // Create a temporary input element to copy the JSON to the clipboard
        let $temp = $('<input>');
        $('body').append($temp);
        $temp.val(json).select();
        // If Clipboard API is unavailable, use the deprecated `execCommand`
        if (!navigator.clipboard) {
            document.execCommand('copy');
            // Otherwise, use the Clipboard API
        } else {
            navigator.clipboard.writeText(json).then(
                function () {
                    console.log('Copied row JSON to clipboard')
                    displayToastTop({
                        type: 'success',
                        string: 'Copied the row to the clipboard as JSON.',
                        title: 'Row Copied'
                    });
                })
                .catch(
                    function () {
                        console.log('Failed to copy row JSON to clipboard')
                    });
        }
        $temp.remove();
    }

    function generateRow(entry) {
        let out = `<tr id="${entry["id"]}" class="editableRow">`;
        columnInfo.forEach(column => {
            let value = column.getValue ? column.getValue(entry) : entry[column.internalName]
            let toHtmlFunc = column.toHtml ?? jsEscape;
            out += `<td class="${column.columnClass} align-middle">${toHtmlFunc(value)}</td>`;
        });
        out += `<td class="optionsColumn align-middle">
            <button class="btn" data-toggle="tooltip" data-placement="left" title="Create a copy of this log entry" onClick="copyEntry(this);" entry-id="${entry['id']}"><i class="fa fa-copy"></i></button>
            <button class="btn" data-toggle="tooltip" data-placement="left" title="Copy this entry to your clipboard as JSON" onClick="convertRowToJSON(${entry["id"]});"><i class="fas fa-clipboard"></i></button>
            <button class="btn danger" data-toggle="tooltip" data-placement="left" title="Delete this log entry" onClick="deleteEntry(this);" entry-id="${entry['id']}"><i class="fa fa-trash"></i></button>
        </td></tr>`;

        return out;
    }

    // Match checkboxes and column IDs to show or hide columns based on the checkbox state
    function coupleCheckboxColumn(checkboxId, columnClass) {
        $(checkboxId).change(function () {
            if (!this.checked) {
                $(columnClass).hide()
                // Add column to hiddenLogTblColumns
                hiddenLogTblColumns.push(columnClass)
            } else {
                $(columnClass).show()
                // Remove column from hiddenLogTblColumns
                hiddenLogTblColumns = hiddenLogTblColumns.filter(value => {
                    return value != columnClass;
                });
            }
            // Save hiddenLogTblColumns to localStorage
            localStorage.setItem('hiddenLogTblColumns', JSON.stringify(hiddenLogTblColumns));
            // Update classes to round corners of first and last header columns
            columnInfo.forEach(column => {
                let $col = $('.' + column.columnClass)
                if ($col.hasClass('first-col')) {
                    $col.removeClass('first-col')
                }
                if ($col.hasClass('last-col')) {
                    $col.removeClass('last-col')
                }
            })
            let firstCol = $('th').filter(':visible').first()
            let lastCol = $('th').filter(':visible').last()
            if (!firstCol.hasClass('first-col')) {
                firstCol.addClass('first-col')
            }
            if (!lastCol.hasClass('last-col')) {
                lastCol.addClass('last-col')
            }
        });
    }

    // Build the column show/hide checkboxes
    function buildColumnsCheckboxes() {
        columnInfo.forEach(column => {
            let checked = (column.showByDefault === undefined || column.showByDefault) ? "checked" : "";
            let checkboxEntry = `
            <div class="form-check-inline">
            <div class="custom-control custom-switch">
            <input type="checkbox" id="${column.checkBoxID}" class="form-check-input custom-control-input" ${checked}/>
            <label class="form-check-label custom-control-label" for="${column.checkBoxID}">${column.prettyName}</label>
            </div>
            </div>
            `
            $checkboxList.append(checkboxEntry)
            // let headerColumn = `
            // <th class="${column.columnClass} align-middle">${column.prettyName}</th>
            // `
            // $tableHeader.append(headerColumn)
            coupleCheckboxColumn('#' + column.checkBoxID, '.' + column.columnClass)

            if (hiddenLogTblColumns.includes('.' + column.columnClass)) {
                $('#' + column.checkBoxID).prop('checked', false)
            }
        })
    }

    // Generate checkboxes for the sanitize confirmation modal
    function buildSanitizeCheckboxes() {
        columnInfo.forEach(column => {
            let checked = (column.sanitizeByDefault === undefined || column.sanitizeByDefault) ? "checked" : "";
            let checkboxEntry = `
            <div class="form-check-inline">
            <div class="custom-control custom-switch">
            <input type="checkbox" name="${column.internalName}" id="sanitize_${column.checkBoxID}" class="form-check-input custom-control-input" ${checked}/>
            <label class="form-check-label custom-control-label" for="sanitize_${column.checkBoxID}">${column.prettyName}</label>
            </div>
            </div>
            `
            $sanitizeCheckboxList.append(checkboxEntry)
        })
    }

    // Hide columns based on the "Select Columns" checkboxes
    function hideColumns() {
        columnInfo.forEach(column => {
            $checkbox = $('#' + column.checkBoxID)
            if (!$checkbox.prop('checked')) {
                $('.' + column.columnClass).hide()
            }
        })
    }

    // Update an existing row with new data from the server
    function updateRow($existingRow, newRow) {
        $(newRow).children().each(function () {
            let className = $(this).attr('class').split(' ')[0]
            $existingRow.find('.' + className).html($(this).html())
        });
    }

    // Create a new entry when the create button is clicked
    window.createEntry = function (id) {
        socket.send(JSON.stringify({
            'action': 'create',
            'oplog_id': id
        }))
        displayToastTop({type: 'success', string: 'Successfully added a log entry.', title: 'Oplog Update'});
    }

    // Delete an entry when the delete button is clicked
    window.deleteEntry = function ($ele) {
        let id = $($ele).attr('entry-id')
        socket.send(JSON.stringify({
            'action': 'delete',
            'oplogEntryId': id
        }))
        displayToastTop({type: 'success', string: 'Successfully deleted a log entry.', title: 'Oplog Update'});
    }

    // Create a copy of an entry when the copy button is clicked
    window.copyEntry = function ($ele) {
        let id = $($ele).attr('entry-id')
        socket.send(JSON.stringify({
            'action': 'copy',
            'oplogEntryId': id
        }))
        displayToastTop({type: 'success', string: 'Successfully cloned a log entry.', title: 'Oplog Update'});
    }

    // Stylize the tags for display in the table
    function stylizeTags(tagString) {
        let tags = tagString.split(',')
        let tagHtml = ''
        for (const tag of tags) {
            if (tag == '') {
                continue
            }
            // Check for escaped version of `att&ck` to style the label
            if (tag.toUpperCase().includes("ATT&AMP;CK") || tag.toUpperCase().includes("ATTACK") || tag.toUpperCase().includes("MITRE") || tag.toUpperCase().includes("TTP")) {
                tagHtml += `<span class="badge badge-danger">${tag}</span>`
            } else if (tag.toUpperCase().includes("CREDS") || tag.toUpperCase().includes("CREDENTIALS")) {
                tagHtml += `<span class="badge badge-warning">${tag}</span>`
            } else if (tag.toUpperCase().includes("VULN")) {
                tagHtml += `<span class="badge badge-success">${tag}</span>`
            } else if (tag.toUpperCase().includes("DETECT")) {
                tagHtml += `<span class="badge badge-info">${tag}</span>`
            } else if (tag.toUpperCase().includes("OBJECTIVE")) {
                tagHtml += `<span class="badge badge-primary">${tag}</span>`
            } else {
                tagHtml += `<span class="badge badge-secondary">${tag}</span>`
            }
        }
        return tagHtml
    }

    function fetch(clear_existing) {
        const new_filter = $searchInput.val();
        const new_offset = clear_existing ? 0 : $tableBody.find('> tr').length;
        if (pendingOperation !== null && pendingOperation.filter === new_filter && pendingOperation.new_offset === new_offset)
            return;

        pendingOperation = {
            filter: new_filter,
            offset: new_offset,
        };
        allEntriesFetched = false;

        if (clear_existing)
            $tableBody.find('tr').remove();
        $oplogTableNoEntries.hide();
        $oplogTableLoading.show();

        socket.send(JSON.stringify({
            'action': 'sync',
            'oplog_id': oplog_id,
            'offset': new_offset,
            'filter': new_filter,
        }));
    }

    function connect() {
        let endpoint = protocol + window.location.host + '/ws' + window.location.pathname
        socket = new WebSocket(endpoint)
        socket.onopen = function () {
            $connectionStatus.html('Connected');
            $connectionStatus.toggleClass('connected');
            errorDisplayed = false;

            $oplogTableLoading.show();
            fetch(true);
        }

        socket.onmessage = function (e) {
            let message = JSON.parse(e.data)

            // Handle the `sync` action that is received whenever the socket (re)connects
            if (message['action'] === 'sync') {
                if (pendingOperation === null || pendingOperation.filter !== message['filter'] || pendingOperation.offset !== message['offset']) {
                    //console.log("Received sync message that did not match pending operation", pendingOperation, message);
                    return;
                }
                pendingOperation = null;

                let entries = message['data']

                if (entries.length !== 0) {
                    entries.forEach(element => {
                        let newRow = generateRow(element);
                        $tableBody.append(newRow);
                    })
                } else {
                    allEntriesFetched = true;
                }
                updatePlaceholder();
                hideColumns();
                $oplogTableLoading.hide();
                $('[data-toggle="tooltip"]').tooltip();
                $table.trigger('updateAll');
                $table.trigger('updateCache');
            } else if (message['action'] === 'create') {
                // Handle the `create` action that is received whenever a new entry is created

                if ($searchInput.val() !== "") {
                    // If there's a filter, refech all, since only the server will know if it matches the filter
                    fetch(true);
                    return;
                }

                let rowFound = false;
                let entry = message['data'];
                let entryId = entry['id'];

                // Check if the row already exists
                $('#oplogTable tbody tr').each(function () {
                    if ($(this).attr('id') === entryId.toString()) {
                        updateRow($(this), generateRow(entry));
                        rowFound = true;
                    }
                });

                // If the row doesn't exist, add it to the table
                if (!rowFound) {
                    $tableBody.prepend(generateRow(entry));
                    let $newRow = $(`#${entry['id']}`);
                    $newRow.hide();

                    emptyTable = false;
                    hideColumns();
                    $newRow.fadeIn(500);
                }
                updatePlaceholder();
                $('[data-toggle="tooltip"]').tooltip();
                $table.trigger('updateAll');
                $table.trigger('updateCache');
            } else if (message['action'] === 'delete') {
                // Handle the `delete` action that is received whenever an entry is deleted
                let id = message['data'];
                $('#oplogTable tbody tr').each(function () {
                    if ($(this).attr('id') === id.toString()) {
                        $(this).fadeOut('slow', function () {
                            $('.tooltip').tooltip('hide');
                            $(this).remove();
                            updatePlaceholder();
                        });
                    }
                });
                $table.trigger('updateAll');
            }
        }

        // Update connection status on error
        socket.onerror = function (e) {
            $connectionStatus.html('Disconnected');
            $connectionStatus.toggleClass('connected');
            console.error('[!] error: ', e);
            socket.close();
            if (!errorDisplayed) {
                displayToastTop({
                    type: 'error',
                    string: 'Websocket has been disconnected.',
                    title: 'Websocket Disconnected'
                });
                errorDisplayed = true;
            }
        }

        // Update connection status on close
        socket.onclose = function () {
            $connectionStatus.html('Disconnected');
            $connectionStatus.toggleClass('connected');
            if (!errorDisplayed) {
                displayToastTop({
                    type: 'error',
                    string: 'Websocket has been disconnected.',
                    title: 'Websocket Disconnected'
                });
                errorDisplayed = true;
            }
            setTimeout(function () {
                console.log('Retrying connection');
                connect();
            }, 5000)
        }
    }

    connect();
    updateColumnInfo(oplog_entry_extra_fields_spec);
    buildColumnsCheckboxes();
    $tableHeader.html(generateTableHeaders());
    buildSanitizeCheckboxes();

    $table.tablesorter(
        {
            cssAsc: 'down', cssDesc: 'up', cssNone: 'none',
            widgets: ['saveSort'],
            widgetOptions: {
                saveSort: true,
                storage_page: 'logDetailTable'
            }
        }
    );

    $('#resetSortBtn').click(function() {
      $table
        .trigger('saveSortReset')
        .trigger('sortReset');
      return false;
    });

    // Show or hide the table column select options
    $('#columnSelectDropdown').click(function () {
        $('#columnSelect').slideToggle('slow');
        $(this).toggleClass('open');
    });

    // Pull additional entries if user scrolls to bottom of ``tbody``
    $tableBody.scroll(function () {
        if (pendingOperation === null) {
            // Check if current scroll position + height of div is >= height of the content
            // True if scroll has reached the bottom

            if ($(this).scrollTop() + $(this).innerHeight() + 1 >= $(this)[0].scrollHeight) {
                if (allEntriesFetched === false) {
                    fetch(false);
                }
            }
        }
    });

    // Open the entry modal when user double-clicks a row
    $tableBody.on('dblclick', '.editableRow', function (e) {
        e.preventDefault();
        let url = window.location.origin + '/oplog/entry/update/' + $(this).attr('id');
        $('.oplog-form-div').load(url, function () {
            $('#edit-modal').modal('toggle');
            tinymceLogInit();
            formAjaxSubmit('#oplog-entry-form', '#edit-modal');
        });
        return false;
    });

    // Submit the entry modal's form with AJAX
    let formAjaxSubmit = function (form, modal) {
        $(form).submit(function (e) {
            e.preventDefault();
            $.ajax({
                type: $(this).attr('method'),
                url: $(this).attr('action'),
                data: $(this).serialize(),
                success: function (xhr) {
                    if ($(xhr).find('.has-error').length > 0) {
                        console.error('error detected')
                        $(modal).find('.oplog-form-div').html(xhr);
                        formAjaxSubmit(form, modal);
                    } else {
                        $(modal).modal('toggle');
                    }
                    tinymceRemove();
                },
                error: function (xhr, ajaxOptions, thrownError) {
                    // Handle response errors here
                }
            });
        });
    }

    $('#edit-modal').on('hide.bs.modal', function () {
        tinymceRemove();
    })

    // Download the log as a CSV file when the user clicks the "Export Entries" menu item
    $('#exportEntries').click(function () {
        let filename = generateDownloadName(oplog_name + '-log-export-' + oplog_id.toString() + '.csv');
        let export_url = $tableBody.attr("data-oplog-export-url");
        download(export_url, filename);
    })

    // Create event to filter results in real-time as search textbox is updated
    let filter_debounce_timeout_id = null;
    $searchInput.on('keyup', function (ev) {
        //let value = $(this).val().toLowerCase();
        //$('#oplogTableBody tr').filter(function () {
        //  $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        //});
        if (filter_debounce_timeout_id !== null) {
            clearTimeout(filter_debounce_timeout_id);
        }
        filter_debounce_timeout_id = setTimeout(function () {
            filter_debounce_timeout_id = null;
            fetch(true);
        }, ev.key === "Enter" ? 0 : 500);
    });

    // Toggle project status with AJAX
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
            }
        });
        $.ajax({
            url: url,
            type: 'POST',
            dataType: 'json',
            data: {
                'oplog': oplogId
            },
            success: function (data) {
                if (data['toggle']) {
                    $toggleLink.removeClass('notification-bell-icon')
                    $toggleLink.addClass('silenced-notification-icon')
                    $toggleLink.text('Notifications: Off')
                } else {
                    $toggleLink.removeClass('silenced-notification-icon')
                    $toggleLink.addClass('notification-bell-icon')
                    $toggleLink.text('Notifications: On')
                }
                if (data['message']) {
                    displayToastTop({type: data['result'], string: data['message'], title: 'Log Update'});
                }
            },
        });
    });

    // Capture CTRL+S and CTRL+N to export the log and create new entries respectively
    $(window).keydown(function (event) {
        if (event.ctrlKey && event.keyCode === 78) {
            event.preventDefault();
            createEntry(oplog_id);
        }

        if (event.ctrlKey && event.keyCode === 83) {
            event.preventDefault();
            let filename = generateDownloadName(oplog_name + '-log-export-' + oplog_id.toString() + '.csv');
            let export_url = $tableBody.attr("data-oplog-export-url");
            download(export_url + oplog_id.toString(), filename);
        }
    });

    // $table.trigger('updateAll');
});
