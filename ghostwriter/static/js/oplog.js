/* JavaScript specific to the log entry view page goes here. */

// Get the array of hidden columns from local storage or set to empty array
let hiddenLogTblColumns = JSON.parse((localStorage.getItem('hiddenLogTblColumns') !== null ? localStorage.getItem('hiddenLogTblColumns') : JSON.stringify([])));

// Assemble the array of column information for the table
let columnInfo = []
columnInfo = [
    ['startDateCheckBox', 'startDateColumn', 'Start Date', 'start_date'],
    ['endDateCheckbox', 'endDateColumn', 'End Date', 'end_date'],
    ['sourceIPCheckbox', 'sourceIPColumn', 'Source', 'source_ip'],
    ['destIPCheckbox', 'destIPColumn', 'Destination', 'dest_ip'],
    ['toolNameCheckbox', 'toolNameColumn', 'Tool Name', 'tool'],
    ['userContextCheckbox', 'userContextColumn', 'User Context', 'user_context'],
    ['commandCheckbox', 'commandColumn', 'Command', 'command'],
    ['descriptionCheckbox', 'descriptionColumn', 'Description', 'description'],
    ['outputCheckbox', 'outputColumn', 'Output', 'output'],
    ['commentsCheckbox', 'commentsColumn', 'Comments', 'comments'],
    ['operatorCheckbox', 'operatorColumn', 'Operator', 'operator_name'],
    ['tagsCheckbox', 'tagsColumn', 'Tags', 'tags'],
    ['optionsCheckbox', 'optionsColumn', 'Options', ''],
]

// Generate a table row based on a log entry
function generateTableHeaders() {
    return `<th class="${columnInfo[0][1]} align-middle">${columnInfo[0][2]}</th>
            <th class="${columnInfo[1][1]} align-middle">${columnInfo[1][2]}</th>
            <th class="${columnInfo[2][1]} align-middle">${columnInfo[2][2]}</th>
            <th class="${columnInfo[3][1]} align-middle">${columnInfo[3][2]}</th>
            <th class="${columnInfo[4][1]} align-middle">${columnInfo[4][2]}</th>
            <th class="${columnInfo[5][1]} align-middle">${columnInfo[5][2]}</th>
            <th class="${columnInfo[6][1]} align-middle">${columnInfo[6][2]}</th>
            <th class="${columnInfo[7][1]} align-middle">${columnInfo[7][2]}</th>
            <th class="${columnInfo[8][1]} align-middle">${columnInfo[8][2]}</th>
            <th class="${columnInfo[9][1]} align-middle">${columnInfo[9][2]}</th>
            <th class="${columnInfo[10][1]} align-middle">${columnInfo[10][2]}</th>
            <th class="${columnInfo[11][1]} align-middle">${columnInfo[11][2]}</th>
            <th class="${columnInfo[12][1]} align-middle"><span class="mr-4">${columnInfo[12][2]}</span></th>`
}

// Generate a table row based on a log entry
function generateRow(entry) {
    return `<tr id="${entry["id"]}" class="editableRow">
            <td class="${columnInfo[0][1]} align-middle">${jsEscape(entry["start_date"]).replace(/\.\d+/, "").replace("Z", "").replace("T", " ")}</td>
            <td class="${columnInfo[1][1]} align-middle">${jsEscape(entry["end_date"]).replace(/\.\d+/, "").replace("Z", "").replace("T", " ")}</td>
            <td class="${columnInfo[2][1]} align-middle">${jsEscape(entry["source_ip"])}</td>
            <td class="${columnInfo[3][1]} align-middle">${jsEscape(entry["dest_ip"])}</td>
            <td class="${columnInfo[4][1]} align-middle">${jsEscape(entry["tool"])}</td>
            <td class="${columnInfo[5][1]} align-middle">${jsEscape(entry["user_context"])}</td>
            <td class="${columnInfo[6][1]} align-middle"><div>${jsEscape(entry["command"])}<div></td>
            <td class="${columnInfo[7][1]} align-middle"><div>${jsEscape(entry["description"])}</div></td>
            <td class="${columnInfo[8][1]} align-middle"><div>${jsEscape(entry["output"])}</div></td>
            <td class="${columnInfo[9][1]} align-middle"><div>${jsEscape(entry["comments"])}</div></td>
            <td class="${columnInfo[10][1]} align-middle">${jsEscape(entry["operator_name"])}</td>
            <td class="${columnInfo[11][1]} align-middle">${stylizeTags(jsEscape(entry["tags"]))}</td>
            <td class="${columnInfo[12][1]} align-middle">
                <button class="btn" onClick="javascript:copyEntry(this);" entry-id="${entry['id']}"><i class="fa fa-copy"></i></button>
                <button class="btn" onClick="javascript:deleteEntry(this);" entry-id="${entry['id']}"><i class="fa fa-trash"></i></button>
            </td>
            </tr>`
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
            hiddenLogTblColumns = hiddenLogTblColumns.filter(function (value, _, _) {
                return value != columnClass;
            });
        }
        // Save hiddenLogTblColumns to localStorage
        localStorage.setItem('hiddenLogTblColumns', JSON.stringify(hiddenLogTblColumns));
        // Update classes to round corners of first and last header columns
        columnInfo.forEach(function (value, _, _) {
            let $col = $('.' + value[1])
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
    columnInfo.forEach(function (value, _, _) {
        let checkboxEntry = `
        <div class="form-check-inline">
        <div class="custom-control custom-switch">
        <input type="checkbox" id="${value[0]}" class="form-check-input custom-control-input" checked/>
        <label class="form-check-label custom-control-label" for="${value[0]}">${value[2]}</label>
        </div>
        </div>
        `
        $checkboxList.append(checkboxEntry)
        let headerColumn = `
        <th class="${value[1]} align-middle">${value[2]}</th>
        `
        $tableHeader.append(headerColumn)
        coupleCheckboxColumn('#' + value[0], '.' + value[1])

        if (hiddenLogTblColumns.includes('.' + value[1])) {
            $('#' + value[0]).prop('checked', false)
        }
    })
}

// Hide columns based on the "Select Columns" checkboxes
function hideColumns() {
    columnInfo.forEach(function (value, _, _) {
        $checkbox = $('#' + value[0])
        if (!$checkbox.prop('checked')) {
            $('.' + value[1]).hide()
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
    displayToastTop({type: 'success', string: 'Successfully added a log entry', title: 'Oplog Update'});
}

// Delete an entry when the delete button is clicked
function deleteEntry($ele) {
    let id = $($ele).attr('entry-id')
    socket.send(JSON.stringify({
        'action': 'delete',
        'oplogEntryId': id
    }))
    displayToastTop({type: 'success', string: 'Successfully deleted a log entry', title: 'Oplog Update'});
}

// Create a copy of an entry when the copy button is clicked
function copyEntry($ele) {
    let id = $($ele).attr('entry-id')
    socket.send(JSON.stringify({
        'action': 'copy',
        'oplogEntryId': id
    }))
    displayToastTop({type: 'success', string: 'Successfully cloned a log entry', title: 'Oplog Update'});
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
