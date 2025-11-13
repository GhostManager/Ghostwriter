/**
 * Evidence Lightbox Functionality
 * Provides full-size viewing of evidence files in a modal overlay
 */

/**
 * Open the evidence lightbox modal with the specified evidence
 * @param {string} evidenceName - The friendly name of the evidence
 * @param {string} evidenceUrl - The URL to download/view the evidence
 * @param {string} evidenceType - The type of evidence ('image' or 'text')
 */
function openEvidenceLightbox(evidenceName, evidenceUrl, evidenceType) {
  // Validate evidenceType
  if (evidenceType !== 'image' && evidenceType !== 'text') {
    console.error('Invalid evidence type:', evidenceType);
    return;
  }

  const $modal = $('#evidence-lightbox-modal');
  const $title = $('#evidence-lightbox-title');
  const $image = $('#evidence-lightbox-image');
  const $textContainer = $('#evidence-lightbox-text');
  const $textPre = $textContainer.find('pre');
  const $download = $('#evidence-lightbox-download');
  const $modalBody = $modal.find('.modal-body');

  // Create loading indicator if it doesn't exist
  let $loadingIndicator = $('#evidence-lightbox-loading');
  if ($loadingIndicator.length === 0) {
    $loadingIndicator = $('<div id="evidence-lightbox-loading" class="text-center" style="padding: 3rem;"><i class="fas fa-spinner fa-spin fa-3x"></i><p class="mt-3">Loading...</p></div>');
    $modalBody.prepend($loadingIndicator);
  }

  // Set modal title and download link
  $title.text(evidenceName);
  $download.attr('href', evidenceUrl);
  $download.attr('download', evidenceName);

  // Hide content and show loading indicator
  $image.hide();
  $textContainer.hide();
  $loadingIndicator.show();

  // Show modal immediately with loading indicator
  $modal.modal('show');

  if (evidenceType === 'image') {
    // Remove any previous event handlers to avoid duplicates
    $image.off('load.evidenceLightbox error.evidenceLightbox');

    // Attach load handler
    $image.on('load.evidenceLightbox', function() {
      $loadingIndicator.hide();
      $image.show();
    });

    // Attach error handler
    $image.on('error.evidenceLightbox', function() {
      $loadingIndicator.hide();
      console.error('Failed to load image');
      if (typeof displayToastTop === 'function') {
        displayToastTop({type: 'error', string: 'Failed to load image'});
      }
      $modal.modal('hide');
    });

    // Set image src and alt (triggers loading)
    $image.attr('alt', evidenceName);
    $image.attr('src', evidenceUrl);
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
        $loadingIndicator.hide();
        $textPre.text(text);
        $textContainer.show();
      })
      .catch(error => {
        $loadingIndicator.hide();
        console.error('Error loading text file:', error);
        if (typeof displayToastTop === 'function') {
          displayToastTop({type: 'error', string: 'Error loading file content'});
        }
        $modal.modal('hide');
        // Fallback: just open download
        window.location.href = evidenceUrl;
      });
  }
}

/**
 * Initialize evidence lightbox event handlers
 * Uses event delegation on document to avoid memory leaks
 * Call this once on page load
 */
function initEvidenceLightbox() {
  // Handle clicks on evidence preview elements to open lightbox
  // Uses event delegation to handle dynamically added modals
  $(document).on('click.evidenceLightbox', '.js-open-lightbox', function(e) {
    e.preventDefault();

    const $element = $(this);
    const evidenceName = $element.data('evidence-name');
    const evidenceUrl = $element.data('evidence-url');
    const evidenceType = $element.data('evidence-type');
    const modalId = $element.data('modal-id');

    // Close the detail modal first
    const $detailModal = $('#' + modalId);
    $detailModal.modal('hide');

    // Wait for detail modal to fully hide before opening lightbox
    $detailModal.one('hidden.bs.modal', function() {
      openEvidenceLightbox(evidenceName, evidenceUrl, evidenceType);
    });
  });

  // Close lightbox when clicking the modal background (not the content)
  $(document).on('click.evidenceLightbox', '#evidence-lightbox-modal .modal-body', function(e) {
    if (e.target === this) {
      $('#evidence-lightbox-modal').modal('hide');
    }
  });

  // Prevent closing when clicking the image or text content
  $(document).on('click.evidenceLightbox', '#evidence-lightbox-modal .modal-body img, #evidence-lightbox-modal .modal-body #evidence-lightbox-text', function(e) {
    e.stopPropagation();
  });
}

// Initialize once on document ready
$(document).ready(function() {
  initEvidenceLightbox();
});