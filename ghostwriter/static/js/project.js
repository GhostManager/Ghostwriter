/* Project specific Javascript goes here. */

// Function to display Toastr notifications
function displayToastTop(type, string, title='', delay=4, escapeHTML=true){
    delay = delay * 1000;
    if ( type === 'error' && delay === 4000) {
        delay = 0;
    }
    toastr.options.timeOut = delay.toString();
    toastr.options.extendedTimeOut = delay.toString();
    toastr.options.escapeHtml = escapeHTML;
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
    if (msg !== undefined){
        msg.css({'width': '100%', 'min-width': '400px', 'white-space': 'pre-wrap'});
    }
}
