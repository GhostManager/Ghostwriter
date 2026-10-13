(function () {
  document.querySelectorAll('[data-formset-prefix]').forEach(function (formset) {
    const prefix = formset.dataset.formsetPrefix;
    const pane = formset.closest('.tab-pane');
    const source = pane && pane.getElementsByClassName('formset-add-' + prefix)[0];
    if (!source) return;

    // Share the original handler, including counts, editor setup, and scrolling.
    function addEntry(event) {
      event.preventDefault();
      const previousCount = formset.querySelectorAll('.formset-container').length;
      source.click();
      const entries = formset.querySelectorAll('.formset-container');
      if (entries.length > previousCount) {
        // Continue keyboard navigation in the new entry rather than at Save.
        const fields = entries[entries.length - 1].querySelectorAll('input, select, textarea');
        const field = Array.from(fields).find(function (input) {
          return !input.disabled && !['hidden', 'button', 'submit'].includes(input.type) &&
            input.getClientRects().length > 0;
        });
        if (field) field.focus({ preventScroll: true });
      }
    }
    function updateActions() {
      formset.querySelectorAll('.formset-container').forEach(function (entry) {
        const actions = entry.querySelector('.formset-actions');
        if (!actions || !actions.querySelector('.formset-del-button')) return;

        let button = actions.querySelector('.collection-add-button');
        if (!button) {
          // Copy only presentation, so each entry has no duplicate field or ID.
          button = document.createElement('button');
          button.type = 'button';
          button.className = source.className;
          button.classList.remove('formset-add-' + prefix);
          button.classList.add('collection-add-button');
          button.textContent = source.value || source.textContent;
          button.setAttribute('aria-controls', formset.id);
          button.addEventListener('click', addEntry);
          actions.appendChild(button);
        }

        const deleted = entry.querySelector('input[name$="-DELETE"]');
        button.hidden = !!deleted && deleted.checked;
      });
    }

    // Only observe list insertions. Rich-text changes inside a card do not need
    // to update collection actions on every keystroke.
    new MutationObserver(updateActions).observe(formset, { childList: true });
    formset.addEventListener('change', function (event) {
      if (event.target.matches('input[name$="-DELETE"]')) updateActions();
    });
    formset.addEventListener('click', function (event) {
      if (event.target.closest('.formset-del-button, .formset-undo-button')) {
        // The existing document handlers set DELETE after this event bubbles.
        window.setTimeout(updateActions, 0);
      }
    });
    updateActions();
  });
})();
