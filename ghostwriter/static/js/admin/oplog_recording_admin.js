(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixRecordingLinks);
    } else {
        fixRecordingLinks();
    }

    function fixRecordingLinks() {
        // Get the recording ID from the URL (e.g., /admin/oplog/oplogentryrecording/123/change/)
        const urlMatch = window.location.pathname.match(/\/oplogentryrecording\/(\d+)\//);
        if (!urlMatch) {
            // We're not on a recording detail page
            return;
        }

        const recordingId = urlMatch[1];

        // Find the "Currently:" link in the recording_file field
        const recordingField = document.querySelector('.field-recording_file p.file-upload a');
        if (recordingField) {
            // Replace the href with our authenticated download URL
            recordingField.href = `/oplog/recording/${recordingId}/download`;
        }
    }
})();
