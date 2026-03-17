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
            title = 'Success';
        }
        msg = toastr.success(string, title);
    } else if (type === 'warning') {
        if (title === '') {
            title = 'Warning';
        }
        msg = toastr.warning(string, title);
    } else if (type === 'error') {
        if (title === '') {
            title = 'Issue Detected';
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
    // Revoke any existing object URL before clearing to prevent memory leaks
    const existingImg = previewDiv.querySelector('img');
    if (existingImg && existingImg.src.startsWith('blob:')) {
      URL.revokeObjectURL(existingImg.src);
    }

    // Clear previous content
    while (previewDiv.firstChild) {
      previewDiv.removeChild(previewDiv.firstChild);
    }

    const objectUrl = URL.createObjectURL(fileInput.files[0]);
    const loadedImage = document.createElement('img');
    loadedImage.alt = 'image';
    loadedImage.style.border = 'thin solid #555555';
    const revokeObjectUrl = function() { URL.revokeObjectURL(objectUrl); };
    loadedImage.addEventListener('load', revokeObjectUrl, { once: true });
    loadedImage.addEventListener('error', revokeObjectUrl, { once: true });
    loadedImage.addEventListener('abort', revokeObjectUrl, { once: true });
    loadedImage.src = objectUrl;
    previewDiv.appendChild(loadedImage);
  }
}

// Insert avatar-specific previews showing how the image will appear in navbar and profile
function renderAvatarPreview(fileInput, previewDiv) {
  if (fileInput.files[0].type.indexOf('image') == 0) {
    // Revoke any existing blob URLs before clearing to prevent leaks when the user
    // selects a new file before the previous images have settled (load/error/abort).
    // Both preview images share the same URL, so track revoked URLs to avoid double-revoking.
    const revokedUrls = new Set();
    previewDiv.querySelectorAll('img').forEach(function(img) {
      if (img.src.startsWith('blob:') && !revokedUrls.has(img.src)) {
        URL.revokeObjectURL(img.src);
        revokedUrls.add(img.src);
      }
    });

    // Clear previous content
    while (previewDiv.firstChild) {
      previewDiv.removeChild(previewDiv.firstChild);
    }

    // Create container
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.justifyContent = 'center';
    container.style.gap = '20px';
    container.style.flexWrap = 'wrap';

    // Create navbar preview section
    const navbarSection = document.createElement('div');
    const navbarLabel = document.createElement('p');
    const navbarStrong = document.createElement('strong');
    navbarStrong.textContent = 'Navbar Preview (40x40)';
    navbarLabel.appendChild(navbarStrong);
    const navbarImg = document.createElement('img');
    navbarImg.alt = 'Navbar preview';
    navbarImg.className = 'navbar-avatar';
    navbarImg.style.position = 'static';
    navbarSection.appendChild(navbarLabel);
    navbarSection.appendChild(navbarImg);

    // Create profile preview section
    const profileSection = document.createElement('div');
    const profileLabel = document.createElement('p');
    const profileStrong = document.createElement('strong');
    profileStrong.textContent = 'Profile Preview (250x250)';
    profileLabel.appendChild(profileStrong);
    const profileImg = document.createElement('img');
    profileImg.alt = 'Profile preview';
    profileImg.className = 'avatar';
    profileImg.style.position = 'static';
    profileSection.appendChild(profileLabel);
    profileSection.appendChild(profileImg);

    // Assemble and append
    container.appendChild(navbarSection);
    container.appendChild(profileSection);
    previewDiv.appendChild(container);

    // Set image sources — revoke the object URL once both images have settled (load, error, or abort)
    const imageUrl = URL.createObjectURL(fileInput.files[0]);
    let settledCount = 0;
    const onSettle = function() {
      settledCount++;
      if (settledCount === 2) { URL.revokeObjectURL(imageUrl); }
    };
    navbarImg.addEventListener('load', onSettle, { once: true });
    navbarImg.addEventListener('error', onSettle, { once: true });
    navbarImg.addEventListener('abort', onSettle, { once: true });
    profileImg.addEventListener('load', onSettle, { once: true });
    profileImg.addEventListener('error', onSettle, { once: true });
    profileImg.addEventListener('abort', onSettle, { once: true });
    navbarImg.src = imageUrl;
    profileImg.src = imageUrl;
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

