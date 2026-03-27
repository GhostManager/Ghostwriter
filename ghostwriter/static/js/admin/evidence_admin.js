(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixEvidenceLinks);
    } else {
        fixEvidenceLinks();
    }

    function fixEvidenceLinks() {
        // Get the evidence ID from the URL (e.g., /admin/reporting/evidence/123/change/)
        const urlMatch = window.location.pathname.match(/\/evidence\/(\d+)\//);
        if (!urlMatch) {
            // We're not on an evidence detail page
            return;
        }

        const evidenceId = urlMatch[1];

        // Find the "Currently:" link in the document field
        const documentField = document.querySelector('.field-document p.file-upload a');
        if (documentField) {
            // Replace the href with our custom evidence_download URL with view parameter
            const downloadUrl = `/reporting/evidence/download/${evidenceId}?view=true`;
            documentField.href = downloadUrl;
            // documentField.target = '_blank';
        }
    }
})();
