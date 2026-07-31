(function (window, $) {
  function initializeWorkingContext() {
    const modal = document.querySelector('[data-working-context-modal]');
    if (!modal) {
      return;
    }

    const catalogUrl = modal.dataset.catalogUrl;
    const pinUrl = modal.dataset.pinUrl;
    const csrfInput = modal.querySelector('[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput ? csrfInput.value : '';
    const list = modal.querySelector('[data-working-context-list]');
    const loading = modal.querySelector('[data-working-context-loading]');
    const empty = modal.querySelector('[data-working-context-empty]');
    const search = modal.querySelector('[data-working-context-search]');
    const completedToggle = modal.querySelector('[data-working-context-completed]');
    const filterButtons = Array.from(modal.querySelectorAll('[data-working-context-filter]'));
    let catalog = null;
    let catalogRequest = null;
    let currentFilter = 'all';
    let pendingQuickAdd = null;

    function createElement(tagName, className, text) {
      const element = document.createElement(tagName);
      if (className) {
        element.className = className;
      }
      if (text !== undefined) {
        element.textContent = text;
      }
      return element;
    }

    function appendIcon(parent, className) {
      const icon = createElement('i', className);
      icon.setAttribute('aria-hidden', 'true');
      parent.appendChild(icon);
      return icon;
    }

    function pinnedKey(itemType, objectId) {
      return itemType + ':' + String(objectId);
    }

    function currentPinnedKeys() {
      if (catalog) {
        return new Set(catalog.pinned_items.map(function (item) {
          return pinnedKey(item.type, item.id);
        }));
      }
      return new Set(
        Array.from(document.querySelectorAll('[data-pinned-work-type][data-pinned-work-id]'))
          .map(function (item) {
            return pinnedKey(item.dataset.pinnedWorkType, item.dataset.pinnedWorkId);
          })
      );
    }

    function configurePinButton(button, itemType, objectId, isPinned, label) {
      button.type = 'button';
      button.classList.add('js-work-pin');
      button.dataset.workType = itemType;
      button.dataset.workId = objectId;
      button.classList.toggle('is-pinned', isPinned);
      button.setAttribute('aria-pressed', String(isPinned));
      button.setAttribute(
        'aria-label',
        (isPinned ? 'Unpin ' : 'Pin ') + label
      );
      button.setAttribute(
        'title',
        isPinned ? 'Remove from pinned work' : 'Pin to sidebar'
      );
    }

    function buildPinButton(itemType, objectId, isPinned, label, className) {
      const button = createElement('button', className || 'working-context-pin');
      configurePinButton(button, itemType, objectId, isPinned, label);
      appendIcon(button, 'fas fa-thumbtack');
      return button;
    }

    function setFilter(filterName) {
      currentFilter = filterName === 'pinned' ? 'pinned' : 'all';
      filterButtons.forEach(function (button) {
        const isActive = button.dataset.workingContextFilter === currentFilter;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-pressed', String(isActive));
      });
      renderCatalog();
    }

    function reportMatches(report, group, query, showCompleted) {
      if (!showCompleted && report.complete) {
        return false;
      }

      if (
        currentFilter === 'pinned'
        && !report.pinned
        && !group.project.pinned
        && !group.client.pinned
      ) {
        return false;
      }

      if (!query) {
        return true;
      }
      return [
        report.label,
        group.project.label,
        group.client.label,
        report.meta,
      ].some(function (value) {
        return String(value || '').toLocaleLowerCase().includes(query);
      });
    }

    function buildReportRow(report) {
      const row = createElement(
        'article',
        'working-context-report-row' + (report.working ? ' is-working' : '')
      );
      row.dataset.reportId = report.id;

      const identity = createElement('div', 'working-context-report-identity');
      const reportLink = createElement('a', 'working-context-report-link');
      reportLink.href = report.url;
      appendIcon(
        reportLink,
        report.working ? 'fas fa-bullseye' : 'far fa-file-alt'
      );
      const title = createElement('span', '', report.label);
      reportLink.appendChild(title);
      identity.appendChild(reportLink);

      const meta = createElement('div', 'working-context-report-meta');
      const status = createElement(
        'span',
        report.complete
          ? 'working-context-status is-complete'
          : 'working-context-status is-draft',
        report.complete ? 'Complete' : 'Draft'
      );
      meta.appendChild(status);
      if (report.delivered) {
        meta.appendChild(
          createElement(
            'span',
            'working-context-status is-delivered',
            'Delivered'
          )
        );
      }
      if (report.recent) {
        const recent = createElement(
          'span',
          'working-context-status is-recent',
          'Recent'
        );
        meta.appendChild(recent);
      }
      identity.appendChild(meta);
      row.appendChild(identity);

      const actions = createElement('div', 'working-context-report-actions');
      actions.appendChild(
        buildPinButton(
          'report',
          report.id,
          report.pinned,
          report.label,
          'working-context-pin'
        )
      );

      const useButton = createElement(
        'button',
        'btn btn-sm working-context-use-report js-activate-report'
      );
      useButton.type = 'button';
      useButton.setAttribute('activate-report-id', report.id);
      useButton.setAttribute('activate-report-url', report.activate_url);
      useButton.setAttribute('activate-report-csrftoken', csrfToken);
      useButton.dataset.reportTitle = report.label;
      useButton.dataset.workingReportUnselectedLabel = 'Use report';
      useButton.setAttribute('aria-pressed', String(report.working));
      if (report.working) {
        useButton.classList.add('selected-report');
        appendIcon(useButton, 'fas fa-bullseye');
        useButton.appendChild(
          createElement('span', '', 'Working report')
        );
        useButton.disabled = true;
      } else {
        appendIcon(useButton, 'fas fa-crosshairs');
        useButton.appendChild(createElement('span', '', 'Use report'));
      }
      actions.appendChild(useButton);
      row.appendChild(actions);
      return row;
    }

    function buildProjectGroup(group, reports) {
      const section = createElement('section', 'working-context-group');

      const clientRow = createElement('div', 'working-context-client-row');
      const clientLink = createElement('a', 'working-context-client-link');
      clientLink.href = group.client.url;
      appendIcon(clientLink, 'fas fa-building');
      clientLink.appendChild(createElement('span', '', group.client.label));
      clientRow.appendChild(clientLink);
      clientRow.appendChild(
        buildPinButton(
          'client',
          group.client.id,
          group.client.pinned,
          group.client.label,
          'working-context-pin'
        )
      );
      section.appendChild(clientRow);

      const projectRow = createElement('div', 'working-context-project-row');
      const projectLink = createElement('a', 'working-context-project-link');
      projectLink.href = group.project.url;
      appendIcon(projectLink, 'fas fa-project-diagram');
      const projectCopy = createElement('span', 'working-context-project-copy');
      projectCopy.appendChild(createElement('strong', '', group.project.label));
      projectCopy.appendChild(
        createElement(
          'small',
          '',
          group.project.complete ? 'Completed project' : reports.length + ' report' + (reports.length === 1 ? '' : 's')
        )
      );
      projectLink.appendChild(projectCopy);
      projectRow.appendChild(projectLink);
      projectRow.appendChild(
        buildPinButton(
          'project',
          group.project.id,
          group.project.pinned,
          group.project.label,
          'working-context-pin'
        )
      );
      section.appendChild(projectRow);

      const reportList = createElement('div', 'working-context-report-list');
      reports.forEach(function (report) {
        reportList.appendChild(buildReportRow(report));
      });
      section.appendChild(reportList);
      return section;
    }

    function renderCatalog() {
      if (!catalog) {
        return;
      }
      const query = search.value.trim().toLocaleLowerCase();
      const showCompleted = completedToggle.checked;
      const fragment = document.createDocumentFragment();
      let visibleReportCount = 0;

      catalog.groups.forEach(function (group) {
        const reports = group.reports.filter(function (report) {
          return reportMatches(report, group, query, showCompleted);
        });
        if (!reports.length) {
          return;
        }
        visibleReportCount += reports.length;
        fragment.appendChild(buildProjectGroup(group, reports));
      });

      list.replaceChildren(fragment);
      list.classList.toggle('d-none', visibleReportCount === 0);
      empty.classList.toggle('d-none', visibleReportCount !== 0);
      syncPinButtons();
    }

    function setLoading(isLoading) {
      loading.classList.toggle('d-none', !isLoading);
      if (isLoading) {
        list.classList.add('d-none');
        empty.classList.add('d-none');
      }
    }

    function loadCatalog(force) {
      if (catalog && !force) {
        renderCatalog();
        return $.Deferred().resolve(catalog).promise();
      }
      if (catalogRequest && !force) {
        return catalogRequest;
      }

      setLoading(true);
      catalogRequest = $.getJSON(catalogUrl)
        .done(function (data) {
          catalog = data;
          renderPinnedSidebar(data.pinned_items);
          renderCatalog();
        })
        .fail(function () {
          empty.querySelector('strong').textContent = 'Report choices could not be loaded';
          empty.querySelector('span').textContent = 'Refresh the page and try again.';
          empty.classList.remove('d-none');
        })
        .always(function () {
          setLoading(false);
          catalogRequest = null;
        });
      return catalogRequest;
    }

    function buildSidebarPinnedItem(item) {
      const row = createElement('li');
      row.dataset.pinnedWorkType = item.type;
      row.dataset.pinnedWorkId = item.id;

      const link = createElement(
        'a',
        'sidebar-navigation-link sidebar-pinned-work-link'
      );
      link.href = item.url;
      link.title = item.label;
      const iconWrap = createElement('span', 'sidebar-navigation-icon');
      appendIcon(iconWrap, item.icon);
      link.appendChild(iconWrap);

      const copy = createElement('span', 'sidebar-pinned-work-copy');
      copy.appendChild(createElement('span', '', item.label));
      copy.appendChild(createElement('small', '', item.meta));
      link.appendChild(copy);
      row.appendChild(link);

      if (item.type === 'report') {
        const target = createElement(
          'button',
          'sidebar-pinned-work-target js-activate-report'
            + (item.working ? ' selected-report' : '')
        );
        target.type = 'button';
        target.setAttribute('activate-report-id', item.id);
        target.setAttribute('activate-report-url', item.activate_url);
        target.setAttribute('activate-report-csrftoken', csrfToken);
        target.dataset.reportTitle = item.label;
        target.setAttribute(
          'aria-label',
          item.working
            ? 'Current working report'
            : 'Use ' + item.label + ' as the working report'
        );
        target.title = item.working
          ? 'Current working report'
          : 'Use for quick-adds';
        appendIcon(
          target,
          item.working ? 'fas fa-bullseye' : 'fas fa-crosshairs'
        );
        row.appendChild(target);
      }
      return row;
    }

    function buildSidebarRailPinnedItem(item) {
      const link = createElement('a', 'sidebar-rail-work-link');
      link.href = item.url;
      link.title = item.label;
      link.setAttribute('aria-label', 'Pinned ' + item.type + ': ' + item.label);
      link.setAttribute('data-bs-toggle', 'tooltip');
      link.setAttribute('data-bs-placement', 'right');
      appendIcon(link, item.icon);
      return link;
    }

    function renderPinnedSidebarRail(items) {
      const pinnedRail = document.querySelector('[data-sidebar-rail-pinned-work]');
      if (!pinnedRail) {
        return;
      }

      pinnedRail.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (item) {
        const tooltip = bootstrap.Tooltip.getInstance(item);
        if (tooltip) {
          tooltip.dispose();
        }
      });

      const fragment = document.createDocumentFragment();
      items.forEach(function (item) {
        fragment.appendChild(buildSidebarRailPinnedItem(item));
      });
      pinnedRail.replaceChildren(fragment);
      pinnedRail.classList.toggle('d-none', items.length === 0);
      pinnedRail.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (item) {
        bootstrap.Tooltip.getOrCreateInstance(item);
      });
    }

    function renderPinnedSidebar(items) {
      const pinnedList = document.querySelector('[data-sidebar-pinned-work-list]');
      const pinnedEmpty = document.querySelector('[data-sidebar-pinned-work-empty]');
      if (!pinnedList || !pinnedEmpty) {
        return;
      }

      const fragment = document.createDocumentFragment();
      items.forEach(function (item) {
        fragment.appendChild(buildSidebarPinnedItem(item));
      });
      pinnedList.replaceChildren(fragment);
      pinnedList.classList.toggle('d-none', items.length === 0);
      pinnedEmpty.classList.toggle('d-none', items.length !== 0);
      renderPinnedSidebarRail(items);
    }

    function syncPinButtons() {
      const pinnedKeys = currentPinnedKeys();
      document.querySelectorAll('.js-work-pin[data-work-type][data-work-id]').forEach(function (button) {
        const isPinned = pinnedKeys.has(
          pinnedKey(button.dataset.workType, button.dataset.workId)
        );
        button.classList.toggle('is-pinned', isPinned);
        button.setAttribute('aria-pressed', String(isPinned));
        const label = button.querySelector('[data-work-pin-label]');
        if (label) {
          label.textContent = isPinned ? 'Unpin from sidebar' : 'Pin to sidebar';
        }
        const icon = button.querySelector('.fa-thumbtack');
        if (icon) {
          icon.classList.toggle('is-pinned', isPinned);
        }
      });
    }

    function togglePin(button) {
      button.disabled = true;
      $.ajax({
        url: pinUrl,
        type: 'POST',
        dataType: 'json',
        data: {
          type: button.dataset.workType,
          id: button.dataset.workId,
        },
        beforeSend: function (xhr, ajaxSettings) {
          if (!csrfSafeMethod(ajaxSettings.type) && !this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
          }
        },
      }).done(function (data) {
        if (data.result !== 'success') {
          return;
        }
        renderPinnedSidebar(data.pinned_items);
        displayToastTop({
          type: 'success',
          string: data.message,
          title: 'Pinned Work',
        });
        loadCatalog(true);
      }).fail(function (xhr) {
        const data = xhr.responseJSON || {};
        displayToastTop({
          type: 'error',
          string: data.message || 'Pinned work could not be updated.',
          title: 'Pinned Work',
        });
      }).always(function () {
        button.disabled = false;
      });
    }

    function currentWorkingReportId() {
      const engagement = document.querySelector('.engagement-context');
      return engagement && engagement.dataset.activeReportId
        ? engagement.dataset.activeReportId
        : '';
    }

    function performQuickAdd(action, reportId) {
      const control = action.control;
      control.disabled = true;
      control.classList.add('is-loading');
      const data = {
        report: reportId,
      };
      data[action.kind] = action.id;

      $.ajax({
        url: action.url,
        type: 'POST',
        dataType: 'json',
        data: data,
        beforeSend: function (xhr, ajaxSettings) {
          if (!csrfSafeMethod(ajaxSettings.type) && !this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', action.csrfToken);
          }
        },
      }).done(function (response) {
        displayToastTop({
          type: response.result,
          string: response.message,
          title: action.kind === 'finding' ? 'Finding Added' : 'Observation Added',
          url: response.url,
        });
      }).fail(function (xhr) {
        const response = xhr.responseJSON || {};
        displayToastTop({
          type: 'error',
          string: response.message || 'The item could not be added to the report.',
          title: 'Quick Add',
        });
      }).always(function () {
        control.disabled = false;
        control.classList.remove('is-loading');
      });
    }

    function handleWorkingReportChanged(event) {
      const reportId = event.detail && event.detail.id;
      if (!reportId) {
        return;
      }

      if (catalog) {
        catalog.active_report_id = Number(reportId);
        catalog.groups.forEach(function (group) {
          group.reports.forEach(function (report) {
            report.working = Number(report.id) === Number(reportId);
          });
        });
        catalog.pinned_items.forEach(function (item) {
          item.working = item.type === 'report'
            && Number(item.id) === Number(reportId);
        });
        renderPinnedSidebar(catalog.pinned_items);
        renderCatalog();
      }

      const modalInstance = bootstrap.Modal.getInstance(modal);
      if (modalInstance) {
        modalInstance.hide();
      }
      if (pendingQuickAdd) {
        const action = pendingQuickAdd;
        pendingQuickAdd = null;
        performQuickAdd(action, reportId);
      }
    }

    modal.addEventListener('show.bs.modal', function (event) {
      const launcher = event.relatedTarget;
      const requestedFilter = launcher
        && launcher.dataset
        && launcher.dataset.workingContextLauncher;
      setFilter(requestedFilter === 'pinned' ? 'pinned' : 'all');
      if (window.matchMedia('(min-width: 576px)').matches) {
        window.setTimeout(function () {
          search.focus({preventScroll: true});
        }, 150);
      }
      loadCatalog(false);
    });

    search.addEventListener('input', renderCatalog);
    completedToggle.addEventListener('change', renderCatalog);
    filterButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        setFilter(button.dataset.workingContextFilter);
      });
    });

    document.addEventListener('click', function (event) {
      const pinButton = event.target.closest('.js-work-pin[data-work-type][data-work-id]');
      if (pinButton) {
        event.preventDefault();
        event.stopPropagation();
        togglePin(pinButton);
        return;
      }

      const quickAdd = event.target.closest('.js-quick-add');
      if (!quickAdd) {
        return;
      }
      event.preventDefault();
      const action = {
        control: quickAdd,
        kind: quickAdd.dataset.quickAddKind,
        id: quickAdd.dataset.quickAddId,
        label: quickAdd.dataset.quickAddLabel,
        csrfToken: quickAdd.dataset.quickAddCsrftoken,
        url: quickAdd.dataset.quickAddUrl,
      };
      const reportId = currentWorkingReportId();
      if (reportId) {
        performQuickAdd(action, reportId);
        return;
      }

      pendingQuickAdd = action;
      setFilter('all');
      bootstrap.Modal.getOrCreateInstance(modal).show(quickAdd);
    });

    document.addEventListener(
      'ghostwriter:working-report-changed',
      handleWorkingReportChanged
    );
    document.addEventListener(
      'ghostwriter:working-report-confirmed',
      handleWorkingReportChanged
    );

    syncPinButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeWorkingContext);
  } else {
    initializeWorkingContext();
  }
})(window, jQuery);
