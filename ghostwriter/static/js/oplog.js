/* JavaScript specific to the log entry view page goes here. */

// Get the array of hidden columns from local storage or set to empty array
let hiddenLogTblColumns = JSON.parse((localStorage.getItem('hiddenLogTblColumns') !== null ? localStorage.getItem('hiddenLogTblColumns') : JSON.stringify([])));

// Assemble the array of column information for the table
let columnInfo = [
    {checkBoxID: 'identifierCheckBox', columnClass: 'identifierColumn', prettyName: 'Identifier', internalName: 'entry_identifier', showByDefault: false, sanitizeByDefault: false},
    {checkBoxID: 'startDateCheckBox', columnClass: 'startDateColumn', prettyName: 'Start Date', internalName: 'start_date', toHtml: entry => jsEscape(entry).replace(/\.\d+/, "").replace("Z", "").replace("T", " "), sanitizeByDefault: false},
    {checkBoxID: 'endDateCheckbox', columnClass: 'endDateColumn', prettyName: 'End Date', internalName: 'end_date', toHtml: entry => jsEscape(entry).replace(/\.\d+/, "").replace("Z", "").replace("T", " "), sanitizeByDefault: false},
    {checkBoxID: 'sourceIPCheckbox', columnClass: 'sourceIPColumn', prettyName: 'Source', internalName: 'source_ip', sanitizeByDefault: true},
    {checkBoxID: 'destIPCheckbox', columnClass: 'destIPColumn', prettyName: 'Destination', internalName: 'dest_ip', sanitizeByDefault: true},
    {checkBoxID: 'toolNameCheckbox', columnClass: 'toolNameColumn', prettyName: 'Tool Name', internalName: 'tool', sanitizeByDefault: false},
    {checkBoxID: 'userContextCheckbox', columnClass: 'userContextColumn', prettyName: 'User Context', internalName: 'user_context', sanitizeByDefault: true},
    {checkBoxID: 'commandCheckbox', columnClass: 'commandColumn', prettyName: 'Command', internalName: 'command', sanitizeByDefault: true},
    {checkBoxID: 'descriptionCheckbox', columnClass: 'descriptionColumn', prettyName: 'Description', internalName: 'description', sanitizeByDefault: true},
    {checkBoxID: 'outputCheckbox', columnClass: 'outputColumn', prettyName: 'Output', internalName: 'output', sanitizeByDefault: true},
    {checkBoxID: 'commentsCheckbox', columnClass: 'commentsColumn', prettyName: 'Comments', internalName: 'comments', sanitizeByDefault: true},
    {checkBoxID: 'operatorCheckbox', columnClass: 'operatorColumn', prettyName: 'Operator', internalName: 'operator_name', sanitizeByDefault: false},
    {checkBoxID: 'tagsCheckbox', columnClass: 'tagsColumn', prettyName: 'Tags', internalName: 'tags', toHtml: entry => stylizeTags(jsEscape(entry)), sanitizeByDefault: false},
]

// Update `columnInfo` with extra fields
function updateColumnInfo(extra_field_specs) {
    extra_field_specs.forEach(spec => {
        let toHtmlFunc;
        if(spec.type === "checkbox") {
            toHtmlFunc = v => v ? `<i class="fas fa-check"></i>` : `<i class="fas fa-times"></i>`;
        } else if(spec.type === "rich_text") {
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
}

// Generate table headers
function generateTableHeaders() {
    let out = "";
    columnInfo.forEach(column => {
        out += `<th class="${column.columnClass} align-middle">${column.prettyName}</th>\n`
    });
    out += `<th class="optionsColumn align-middle">Options</th>`;
    return out;
}

// Convert a table row to JSON and copy it to the clipboard
function convertRowToJSON(row_id) {
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

// Add a placeholder row that spans the entire table
function addPlaceholderRow($table) {
    console.log('adding placeholder row')
    $table.prepend(`<tr id="oplogTableNoEntries"><td colspan="100%">No entries to display</td></tr>`)
}

// Remove the placeholder row that spans the entire table
function removePlaceholderRow($table) {
    $table.find('#oplogTableNoEntries').remove()
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
        let headerColumn = `
        <th class="${column.columnClass} align-middle">${column.prettyName}</th>
        `
        $tableHeader.append(headerColumn)
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
function createEntry(id) {
    socket.send(JSON.stringify({
        'action': 'create',
        'oplog_id': id
    }))
    displayToastTop({type: 'success', string: 'Successfully added a log entry.', title: 'Oplog Update'});
}

// Delete an entry when the delete button is clicked
function deleteEntry($ele) {
    let id = $($ele).attr('entry-id')
    socket.send(JSON.stringify({
        'action': 'delete',
        'oplogEntryId': id
    }))
    displayToastTop({type: 'success', string: 'Successfully deleted a log entry.', title: 'Oplog Update'});
}

// Create a copy of an entry when the copy button is clicked
function copyEntry($ele) {
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
    for (tag of tags) {
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
