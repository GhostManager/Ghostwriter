(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixTemplateLinks);
    } else {
        fixTemplateLinks();
    }

    function fixTemplateLinks() {
        // Get the template ID from the URL (e.g., /admin/reporting/reporttemplate/123/change/)
        const urlMatch = window.location.pathname.match(/\/reporttemplate\/(\d+)\//);
        if (!urlMatch) {
            // We're not on a template detail page
            return;
        }

        const templateId = urlMatch[1];

        // Find the "Currently:" link in the document field
        const documentField = document.querySelector('.field-document p.file-upload a');
        if (documentField) {
            // Replace the href with our custom template_download URL
            const downloadUrl = `/reporting/templates/download/${templateId}?download=true`;
            documentField.href = downloadUrl;
        }
    }
})();
