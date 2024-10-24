/* Project-specific JavaScript goes here. */

// Function to display Toastr notifications
function displayToastTop({
                             type,
                             string,
                             title = '',
                             delay = 3,
                             escapeHTML = true,
                             context = null,
                             url = '',
                         }) {
    if (context !== null) {
        if (context === 'form') {
            title = 'Form Validation Error';
        }
    }
    delay = delay * 1000;
    toastr.options.timeOut = delay.toString();
    toastr.options.extendedTimeOut = delay.toString();
    toastr.options.escapeHtml = escapeHTML;
    toastr.options.progressBar = true;
    toastr.options.closeButton = true;
    if (url !== '') {
        toastr.options.onclick = function () {
            window.location.href = url;
        }
    }
    let msg;
    if (type === 'success') {
        if (title === '') {
            title = 'Great Success';
        }
        msg = toastr.success(string, title);
    } else if (type === 'warning') {
        if (title === '') {
            title = 'Beware';
        }
        msg = toastr.warning(string, title);
    } else if (type === 'error') {
        if (title === '') {
            title = 'Great Failure';
        }
        msg = toastr.error(string, title);
    } else if (type === 'info') {
        if (title === '') {
            title = 'FYI';
        }
        msg = toastr.info(string, title);
    } else {
        if (title === '') {
            title = 'Beware';
        }
        msg = toastr.warning(string, title);
    }
    if (msg !== undefined) {
        msg.css({
            'width': '100%',
            'min-width': '400px',
            'white-space': 'pre-wrap',
        });
    }
}

// Check of method should require CSRF protection
function csrfSafeMethod(method) {
    // These HTTP methods do not require CSRF protection
    return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

// Generate a filename for a download with the current date and time
function generateDownloadName(name) {
    let d = new Date();
    let year = d.getFullYear();
    let month = d.getMonth() + 1;
    let day = d.getDate();
    let hour = d.getHours();
    let minutes = d.getMinutes();
    let sec = d.getSeconds();
    if (hour < 10) {
        hour = '0' + hour;
    }
    if (minutes < 10) {
        minutes = '0' + minutes;
    }
    if (day < 10) {
        day = '0' + day;
    }
    if (month < 10) {
        month = '0' + month;
    }
    return '' + year + month + day + '_' + hour + minutes + sec + '_' + name
}

// Update the status badges on the tab bar
function update_badges() {
    // Get the update URL from the ``nav-tabs`` element
    let navTabs = $('.nav-tabs');
    let update_url = navTabs.attr('js-update-tabs-url');
    if (update_url != null) {
        console.log('Updating badges...');
        // Save the ``id`` of the current tab with the ``active`` class
        let activeTabId = $('ul#tab-bar a.active').attr('id');
        activeTabId = '#' + activeTabId;
        // Refresh the HTML from the update URL
        navTabs.html('').load(update_url, function () {
            // Set the previously active tab back to ``active``
            let targetTab = $(activeTabId);
            targetTab.tab('show');
        });
    }
}

// Escape HTML characters in a string to make it safe for display
function jsEscape(s) {
    if (s) {
        return s.toString().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
    } else {
        return '';
    }
}

// Download a file from a URL and save it with a given filename
function download(url, filename) {
    fetch(url).then(function (t) {
        return t.blob().then((b) => {
            let a = document.createElement('a');
            a.href = URL.createObjectURL(b);
            a.setAttribute('download', filename);
            a.click();
        });
    });
}

// Script for Copying Text to Clipboard
function copyToClipboard(element) {
    let $temp = $('<input>');
    $('body').append($temp);
    $temp.val($(element).text().trim()).select();
    // If Clipboard API is unavailable, use the deprecated `execCommand`
    if (!navigator.clipboard) {
        document.execCommand('copy');
        // Otherwise, use the Clipboard API
    } else {
        navigator.clipboard.writeText($(element).text().trim()).then(
            function () {
                console.log('Copied element to clipboard')
            })
            .catch(
                function () {
                    console.log('Failed to copy element to clipboard')
                });
    }
    $temp.remove();
}

// Animate the hamburger menu when opened
function hamburger(x) {
    x.classList.toggle('change');
}

// Prepare the CVSS calculator for findings
function prepareCVSSCalc() {
    let cvss = document.getElementById('id_cvss_vector')
    if (cvss != null) {
        ParseVector(cvss.value);
        CVSSAutoCalc();
        console.log('CVSS calculator is ready')
    }
}

// Show/hide a given table row and toggle the given button's ``open`` class
function showHideRow(btn, row) {
    btn.toggleClass('open');
    $('#' + row).slideToggle(500);
}

// Insert a preview for pasted or selected image files
function renderPreview(fileInput, previewDiv) {
  if (fileInput.files[0].type.indexOf('image') == 0) {
    previewDiv.innerHTML = '<img id="loadedImage" alt="image"/ >'
    let loadedImage = document.getElementById('loadedImage')
    loadedImage.src = URL.createObjectURL(fileInput.files[0])
    loadedImage.style.border = 'thin solid #555555';
  }
}

// Escape HTML characters in a string to make it safe for display
const escapeHtml = (unsafe) => {
    return unsafe.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}


function update_project_contacts() {
  // Get the update URL from the ``nav-tabs`` element
  let $contactsSection = $('#project-contacts');
  let update_url = $contactsSection.attr('js-update-contacts-url');
  if (update_url != null) {
    console.log("Updating contacts...");
    // Refresh the HTML from the update URL
    $contactsSection.html('').load(update_url, function () {
    });
  }
}

