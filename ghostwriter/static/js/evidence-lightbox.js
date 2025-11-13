/**
 * Evidence Lightbox Functionality
 * Provides full-size viewing of evidence files in a modal overlay
 */

// Configuration constants
const MAX_TEXT_PREVIEW_SIZE = 1024 * 1024; // 1MB - files larger than this will show a warning
const MAX_TEXT_DISPLAY_LINES = 10000; // Maximum number of lines to display

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
  const $loadingIndicator = $('#evidence-lightbox-loading');

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

    // Handle cached images: if already loaded, trigger the load handler
    if ($image[0].complete) {
      $image.trigger('load.evidenceLightbox');
    }
  } else {
    // Fetch and show text file content with size limits
    fetch(evidenceUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to load file content');
        }

        // Check content length header if available
        const contentLength = response.headers.get('content-length');
        if (contentLength && parseInt(contentLength) > MAX_TEXT_PREVIEW_SIZE) {
          // File is too large - show warning instead
          $loadingIndicator.hide();
          const sizeInMB = (parseInt(contentLength) / (1024 * 1024)).toFixed(2);
          $textPre.html(
            `<div class="alert alert-warning" role="alert">
              <i class="fas fa-exclamation-triangle"></i>
              <strong>File Too Large for Preview</strong><br>
              This file is ${sizeInMB} MB, which is too large to display in the browser.<br>
              <p class="mt-2 mb-0">Please download the file to view its contents.</p>
            </div>`
          );
          $textContainer.show();
          return null; // Skip text processing
        }

        return response.text();
      })
      .then(text => {
        if (text === null) {
          // File was too large, already handled above
          return;
        }

        // Check if text is too long (even if size check passed)
        const lines = text.split('\n');
        if (lines.length > MAX_TEXT_DISPLAY_LINES) {
          // Truncate and show warning
          const truncatedText = lines.slice(0, MAX_TEXT_DISPLAY_LINES).join('\n');
          $textPre.text(truncatedText);

          // Add warning banner at the top
          $textContainer.prepend(
            `<div class="alert alert-info mb-2" role="alert">
              <i class="fas fa-info-circle"></i>
              Showing first ${MAX_TEXT_DISPLAY_LINES.toLocaleString()} lines of ${lines.length.toLocaleString()} total lines.
              Download the file to view complete contents.
            </div>`
          );
        } else {
          $textPre.text(text);
        }

        $loadingIndicator.hide();
        $textContainer.show();
      })
      .catch(error => {
        $loadingIndicator.hide();
        console.error('Error loading text file:', error);
        if (typeof displayToastTop === 'function') {
          displayToastTop({type: 'error', string: 'Error loading file content'});
        }
        $modal.modal('hide');

        // Fallback: trigger download
        const a = document.createElement('a');
        a.href = evidenceUrl;
        a.download = evidenceName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      });
  }
}

/**
 * Initialize evidence lightbox event handlers
 * Uses event delegation on document to avoid memory leaks
 * Call this once on page load
 */
function initEvidenceLightbox() {
  // Create loading indicator once during initialization
  const $modal = $('#evidence-lightbox-modal');
  const $modalBody = $modal.find('.modal-body');
  const $image = $('#evidence-lightbox-image');
  const $textContainer = $('#evidence-lightbox-text');
  const $textPre = $textContainer.find('pre');
  const $loadingIndicator = $('<div id="evidence-lightbox-loading" class="text-center" style="padding: 3rem; display: none;"><i class="fas fa-spinner fa-spin fa-3x"></i><p class="mt-3">Loading...</p></div>');

  if ($('#evidence-lightbox-loading').length === 0) {
    $modalBody.prepend($loadingIndicator);
  }

  // Clean up when modal is closed to prevent memory leaks
  $modal.on('hidden.bs.modal.evidenceLightbox', function() {
    // Remove image event handlers
    $image.off('load.evidenceLightbox error.evidenceLightbox');

    // Clear image source to stop any pending loads
    $image.attr('src', '');
    $image.attr('alt', '');

    // Clear text content and any warning banners
    $textPre.text('');
    $textContainer.find('.alert').remove();

    // Hide all content and show loading indicator for next use
    $image.hide();
    $textContainer.hide();
    $loadingIndicator.show();
  });

  // Handle clicks on evidence preview elements to open lightbox
  // Uses event delegation to handle dynamically added modals
  $(document).on('click.evidenceLightbox', '.js-open-lightbox', function(e) {
    e.preventDefault();

    const $element = $(this);
    const evidenceName = $element.data('evidence-name');
    const evidenceUrl = $element.data('evidence-url');
    const evidenceType = $element.data('evidence-type');
    const modalId = $element.data('modal-id');

    // Close the detail modal first, but only if it exists and is shown
    const $detailModal = $('#' + modalId);
    if ($detailModal.length && $detailModal.hasClass('show')) {
      $detailModal.one('hidden.bs.modal', function() {
        openEvidenceLightbox(evidenceName, evidenceUrl, evidenceType);
      });
      $detailModal.modal('hide');
    } else {
      openEvidenceLightbox(evidenceName, evidenceUrl, evidenceType);
    }
  });

  // Close lightbox when clicking outside the modal content
  // Use Bootstrap's built-in backdrop click detection
  $modal.on('click.evidenceLightbox', function(e) {
    // Check if click is directly on the modal backdrop (not on modal-dialog or its children)
    if ($(e.target).hasClass('modal')) {
      $modal.modal('hide');
    }
  });
}

// Initialize once on document ready
$(document).ready(function() {
  initEvidenceLightbox();
});