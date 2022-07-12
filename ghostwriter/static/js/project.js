/* Project specific Javascript goes here. */

// Function to display Toastr notifications
function displayToastTop({
  type,
  string,
  title = '',
  delay = 3,
  escapeHTML = true,
  context = null,
}) {
  if (context !== null) {
    if (context == 'form') {
      title = 'Form Validation Error';
    }
  }
  delay = delay * 1000;
  toastr.options.timeOut = delay.toString();
  toastr.options.extendedTimeOut = delay.toString();
  toastr.options.escapeHtml = escapeHTML;
  toastr.options.progressBar = true;
  toastr.options.closeButton = true;
  let msg;
  if (type === 'success') {
    if (title == '') {
      title = 'Great Success';
    }
    msg = toastr.success(string, title);
  } else if (type === 'warning') {
    if (title == '') {
      title = 'Beware';
    }
    msg = toastr.warning(string, title);
  } else if (type === 'error') {
    if (title == '') {
      title = 'Great Failure';
    }
    msg = toastr.error(string, title);
  } else if (type === 'info') {
    if (title == '') {
      title = 'FYI';
    }
    msg = toastr.info(string, title);
  } else {
    if (title == '') {
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

function generateDownloadName(name) {
    var d = new Date();
    var year = d.getFullYear();
    var month = d.getMonth() + 1;
    var day = d.getDate();
    var hour = d.getHours();
    var minutes = d.getMinutes();
    var sec = d.getSeconds();
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
    filename = '' + year + month + day + '_' + hour + minutes + sec + '_' + name
    return filename
}

function update_badges() {
  // Get the update URL from the ``nav-tabs`` element
  var navTabs = $('.nav-tabs');
  var update_url = navTabs.attr('js-update-tabs-url');
  if (update_url != null) {
      console.log("Updating badges...");
      // Save the ``id`` of the current tab with the ``active`` class
      var activeTabId = $('ul#tab-bar a.active').attr('id');
      activeTabId = '#' + activeTabId;
      // Refresh the HTML from the update URL
      navTabs.html('').load(update_url, function() {
          // Set the previously active tab back to ``active``
          var targetTab = $(activeTabId);
          targetTab.tab('show');
      });
  }
}
