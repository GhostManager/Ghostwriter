/**
 * Evidence Lightbox Functionality
 * Provides full-size viewing of evidence files in a modal overlay
 */

/**
 * Open the evidence lightbox modal with the specified evidence
 * @param {number} evidenceId - The ID of the evidence file
 * @param {string} evidenceName - The friendly name of the evidence
 * @param {string} evidenceUrl - The URL to download/view the evidence
 * @param {string} evidenceType - The type of evidence ('image' or 'text')
 */
function openEvidenceLightbox(evidenceId, evidenceName, evidenceUrl, evidenceType) {
  const $modal = $('#evidence-lightbox-modal');
  const $title = $('#evidence-lightbox-title');
  const $image = $('#evidence-lightbox-image');
  const $textContainer = $('#evidence-lightbox-text');
  const $textPre = $textContainer.find('pre');
  const $download = $('#evidence-lightbox-download');

  // Set modal title and download link
  $title.text(evidenceName);
  $download.attr('href', evidenceUrl);
  $download.attr('download', evidenceName);

  if (evidenceType === 'image') {
    // Show image preview
    $image.attr('src', evidenceUrl);
    $image.attr('alt', evidenceName);
    $image.show();
    $textContainer.hide();
  } else {
    // Fetch and show text file content
    fetch(evidenceUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load file content');
        }
        return response.text();
      })
      .then(text => {
        $textPre.text(text);
        $textContainer.show();
        $image.hide();
      })
      .catch(error => {
        console.error('Error loading text file:', error);
        if (typeof displayToastTop === 'function') {
          displayToastTop({type: 'error', string: 'Error loading file content'});
        }
        // Fallback: just open download
        window.location.href = evidenceUrl;
      });
  }

  $modal.modal('show');
}

/**
 * Initialize evidence lightbox event handlers
 * Call this on page load
 */
function initEvidenceLightbox() {
  // Close lightbox when clicking the modal background
  $('#evidence-lightbox-modal .modal-body').click(function(e) {
    if (e.target === this) {
      $('#evidence-lightbox-modal').modal('hide');
    }
  });

  // Prevent closing when clicking the content
  $('#evidence-lightbox-modal .modal-body img, #evidence-lightbox-modal .modal-body #evidence-lightbox-text').click(function(e) {
    e.stopPropagation();
  });
}

// Initialize on document ready
$(document).ready(function() {
  initEvidenceLightbox();
});