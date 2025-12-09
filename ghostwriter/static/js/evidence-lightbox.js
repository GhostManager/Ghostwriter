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
      console.log('Image load success:', evidenceUrl);
      $loadingIndicator.hide();
      $image.show();

      // Dynamically adjust modal width based on image dimensions
      const img = $image[0];
      const imageWidth = img.naturalWidth;
      // const imageHeight = img.naturalHeight;
      const viewportWidth = $(window).width();
      // const viewportHeight = $(window).height();

      // Calculate optimal modal width (90% of viewport or image width, whichever is smaller)
      let modalWidth = Math.min(imageWidth + 100, viewportWidth * 0.9);

      // For very wide images, cap at 95vw
      if (modalWidth > viewportWidth * 0.95) {
        modalWidth = viewportWidth * 0.95;
      }

      // Set minimum width
      if (modalWidth < 500) {
        modalWidth = 500;
      }

      // Apply the width to the modal dialog
      const $modalDialog = $modal.find('.modal-dialog');
      $modalDialog.css('max-width', modalWidth + 'px');
    });

    // Attach error handler
    $image.on('error.evidenceLightbox', function() {
      console.log('Image load error:', evidenceUrl);
      $loadingIndicator.hide();
      console.error('Failed to load image:', evidenceUrl);
      if (typeof displayToastTop === 'function') {
        displayToastTop({type: 'error', string: 'Failed to load image: ' + evidenceName});
      }
      $modal.modal('hide');
    });

    // Set alt and src together - no delay needed
    $image.attr('alt', evidenceName);
    $image.attr('src', evidenceUrl);

    // Handle cached images: if already loaded, trigger the load handler
    if ($image[0].complete && $image[0].naturalHeight !== 0) {
      $image.trigger('load.evidenceLightbox');
    }
  } else {
    // Text file handling
    $image.hide();
    $textContainer.show();
    $textPre.text('Loading...');

    // Set a wider modal width for text files
    const $modalDialog = $modal.find('.modal-dialog');
    const viewportWidth = $(window).width();
    let modalWidth = Math.min(viewportWidth * 0.85, 1200); // 85% of viewport or 1200px max

    // Set minimum width
    if (modalWidth < 700) {
      modalWidth = 700;
    }

    $modalDialog.css('max-width', modalWidth + 'px');

    // Fetch and display text content
    fetch(evidenceUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.text();
      })
      .then(text => {
        $loadingIndicator.hide();

        // Check file size and line count
        const lines = text.split('\n');
        if (text.length > MAX_TEXT_PREVIEW_SIZE) {
          $textPre.html(
            `<div class="alert alert-warning" role="alert">
              <i class="fas fa-exclamation-triangle"></i>
              <strong>Large File Warning</strong><br>
              This file is ${(text.length / 1024 / 1024).toFixed(2)}MB and may take a moment to display.
            </div>`
          );
          // Still show the content after a brief delay
          setTimeout(() => {
            $textPre.text(text);
          }, 100);
        } else if (lines.length > MAX_TEXT_DISPLAY_LINES) {
          const truncatedText = lines.slice(0, MAX_TEXT_DISPLAY_LINES).join('\n');
          $textPre.html(
            `<div class="alert alert-info mb-3" role="alert">
              <i class="fas fa-info-circle"></i>
              Showing first ${MAX_TEXT_DISPLAY_LINES} lines of ${lines.length.toLocaleString()} total lines.
              Download the file to view the complete content.
            </div>` +
            $('<div>').text(truncatedText).html()
          );
        } else {
          $textPre.text(text);
        }
      })
      .catch(error => {
        console.error('Error loading text file:', error);
        $loadingIndicator.hide();
        $textPre.html(
          `<div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-circle"></i>
            <strong>Failed to Load File</strong><br>
            Unable to load the text file content. Please try downloading it instead.
          </div>`
        );
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