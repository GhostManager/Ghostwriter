(function() {
    'use strict';

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixProfileLinks);
    } else {
        fixProfileLinks();
    }

    function fixProfileLinks() {
        // Find the avatar_download_link field which has the correct URL
        const avatarDownloadLink = document.querySelector('.field-avatar_download_link a');
        if (!avatarDownloadLink) {
            // avatar_download_link field not found
            return;
        }

        // Get the correct download URL from the avatar_download_link field
        const downloadUrl = avatarDownloadLink.href;

        // Find the "Currently:" link in the avatar field
        const avatarField = document.querySelector('.field-avatar p.file-upload a');
        if (avatarField) {
            // Replace the href with the correct download URL
            avatarField.href = downloadUrl;
        }
    }
})();
