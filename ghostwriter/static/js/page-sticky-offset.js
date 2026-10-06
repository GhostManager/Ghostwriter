(function () {
  const context = document.querySelector('.engagement-context');
  const content = document.getElementById('content');
  if (!context || !content) return;
  const workspace = content.querySelector('.report-field-workspace');

  function updateOffset() {
    const style = getComputedStyle(context);
    const gap = parseFloat(style.top) || 0;
    const offset = style.position === 'sticky' && context.getClientRects().length
      ? context.getBoundingClientRect().height + gap * 2
      : 0;
    content.style.setProperty('--gw-page-sticky-top', offset + 'px');
    if (workspace) {
      // Use the actual page space, including a bar with no working report selected.
      const top = workspace.getBoundingClientRect().top + window.scrollY;
      workspace.style.setProperty('--gw-report-workspace-top', top + 'px');
      workspace.style.setProperty('--gw-report-workspace-bottom', getComputedStyle(content).paddingBottom);
    }
  }

  // The bar can wrap after resizing, expanding navigation, or switching reports.
  new ResizeObserver(updateOffset).observe(context);
  new MutationObserver(updateOffset).observe(context, {
    attributes: true,
    attributeFilter: ['class'],
  });
  window.addEventListener('resize', updateOffset, { passive: true });
  updateOffset();
})();
