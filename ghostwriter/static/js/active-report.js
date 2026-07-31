(function (window, $) {
  const DEFAULT_STORAGE_KEY = 'ghostwriter-active-report';

  function initActiveReport(options) {
    const settings = $.extend({
      storageKey: DEFAULT_STORAGE_KEY,
      reportUrlTemplate: '',
      activationUrlTemplate: '',
      redirectToShortcutAfterMessage: false,
    }, options || {});

    function templateUrl(template, reportId) {
      return template ? template.replace(/\/0(?=\/|$)/, '/' + reportId) : '';
    }

    function getActiveReportUrl(reportId) {
      return templateUrl(settings.reportUrlTemplate, reportId);
    }

    function getActivationUrl(reportId) {
      return templateUrl(settings.activationUrlTemplate, reportId);
    }

    function getActiveReportLink(reportId) {
      return $('.js-activate-report[activate-report-id="' + reportId + '"]').first();
    }

    function getCsrfToken(element) {
      const elementToken = element
        ? element.getAttribute('activate-report-csrftoken')
        : '';
      const formToken = document.querySelector('[name="csrfmiddlewaretoken"]');
      return elementToken || (formToken ? formToken.value : '');
    }

    function getStoredActiveReport() {
      try {
        return JSON.parse(localStorage.getItem(settings.storageKey));
      } catch (error) {
        try {
          localStorage.removeItem(settings.storageKey);
        } catch (storageError) {}
        return null;
      }
    }

    function storeActiveReport(reportId, reportTitle, contextData) {
      const payload = $.extend({
        id: Number(reportId),
        title: reportTitle || '',
      }, contextData || {});
      try {
        localStorage.setItem(settings.storageKey, JSON.stringify(payload));
      } catch (error) {}
      return payload;
    }

    function clearStoredActiveReport() {
      try {
        localStorage.removeItem(settings.storageKey);
      } catch (error) {}
    }

    function shellContext() {
      const engagement = document.querySelector('.engagement-context');
      if (!engagement || !engagement.dataset.activeReportId) {
        return null;
      }
      return {
        id: Number(engagement.dataset.activeReportId),
        title: engagement.dataset.activeReportTitle || '',
        report_url: engagement.dataset.activeReportUrl || '',
        report_complete: engagement.dataset.activeReportComplete === 'true',
        report_delivered: engagement.dataset.activeReportDelivered === 'true',
        client: engagement.dataset.activeClient || '',
        client_url: engagement.dataset.activeClientUrl || '',
        project: engagement.dataset.activeProject || '',
        project_url: engagement.dataset.activeProjectUrl || '',
      };
    }

    function updateActivationControls(reportId) {
      $('.js-activate-report').each(function () {
        const control = this;
        const isWorking = String(control.getAttribute('activate-report-id')) === String(reportId);
        const label = control.querySelector('[data-working-report-action-label]');
        const icon = control.querySelector('.fa-crosshairs, .fa-bullseye');

        if (!control.dataset.workingReportDefaultLabel && label) {
          control.dataset.workingReportDefaultLabel = (
            control.dataset.workingReportUnselectedLabel
            || (isWorking ? 'Use report' : label.textContent.trim())
          );
        }

        control.classList.toggle('selected-report', isWorking);
        control.classList.remove('toggle-on-icon', 'toggle-off-icon');
        control.setAttribute('aria-pressed', String(isWorking));
        control.setAttribute(
          'title',
          isWorking ? 'Current working report' : 'Use this report for library quick-adds'
        );

        if (label) {
          label.textContent = isWorking
            ? 'Working report'
            : (control.dataset.workingReportDefaultLabel || 'Use report');
        }
        if (icon) {
          icon.classList.toggle('fa-bullseye', isWorking);
          icon.classList.toggle('fa-crosshairs', !isWorking);
        }
      });
    }

    function updateQuickAddControls(reportTitle) {
      document.querySelectorAll('.js-quick-add').forEach(function (control) {
        const itemLabel = control.dataset.quickAddLabel || 'item';
        const description = reportTitle
          ? 'Add ' + itemLabel + ' to ' + reportTitle
          : 'Choose a working report to add ' + itemLabel;
        control.setAttribute('title', description);
        control.setAttribute('aria-label', description);
      });

      document.querySelectorAll('.working-report-guidance-action').forEach(function (control) {
        control.textContent = reportTitle ? 'Change' : 'Choose report';
      });
      document.querySelectorAll('[data-working-report-guidance-detail]').forEach(function (detail) {
        detail.textContent = reportTitle
          ? 'Quick-adds will create a copy in this report.'
          : 'Choose a report before using a quick-add action.';
      });
    }

    function updateEngagementContext(reportId, reportTitle, contextData) {
      const engagement = $('.engagement-context');
      if (!engagement.length) {
        return;
      }

      const reportUrl = contextData && contextData.report_url
        ? contextData.report_url
        : getActiveReportUrl(reportId);
      const normalized = $.extend({
        report_url: reportUrl,
        report_complete: false,
        report_delivered: false,
        client: '',
        client_url: '',
        project: '',
        project_url: '',
      }, contextData || {});

      engagement
        .attr({
          'data-active-report-id': reportId,
          'data-active-report-title': reportTitle || '',
          'data-active-report-url': reportUrl,
          'data-active-client': normalized.client || '',
          'data-active-client-url': normalized.client_url || '',
          'data-active-project': normalized.project || '',
          'data-active-project-url': normalized.project_url || '',
          'data-active-report-complete': String(Boolean(normalized.report_complete)),
          'data-active-report-delivered': String(Boolean(normalized.report_delivered)),
        })
        .addClass('engagement-context-active');
      engagement.find('.engagement-context-empty').addClass('d-none');
      engagement.find('.engagement-context-details').removeClass('d-none');

      const reportLink = engagement.find('.engagement-context-report')
        .attr('href', reportUrl)
        .attr('title', reportTitle || 'Working report');
      reportLink.find('.engagement-context-report-text').text(reportTitle || 'Working report');

      engagement.find('.engagement-context-client')
        .attr('href', normalized.client_url)
        .attr('title', normalized.client)
        .find('.engagement-context-client-text')
        .text(normalized.client);
      engagement.find('.engagement-context-project')
        .attr('href', normalized.project_url)
        .attr('title', normalized.project)
        .find('.engagement-context-project-text')
        .text(normalized.project);
      engagement.find('.engagement-context-report-status')
        .text(normalized.report_complete ? 'Complete' : 'Draft');
      engagement.find('.engagement-context-delivery-status')
        .text(normalized.report_delivered ? 'Delivered' : 'Not delivered');

      document.querySelectorAll('[data-working-report-title]').forEach(function (title) {
        title.textContent = reportTitle || 'Choose a report';
      });
      document.querySelectorAll('[data-working-report-switch-label]').forEach(function (label) {
        label.textContent = 'Switch report';
      });
      document.querySelectorAll('.sidebar-working-report, .sidebar-working-context-action').forEach(function (control) {
        control.classList.add('has-working-report');
        const icon = control.querySelector('.fa-crosshairs, .fa-bullseye');
        if (icon) {
          icon.classList.remove('fa-crosshairs');
          icon.classList.add('fa-bullseye');
        }
      });
      document.querySelectorAll('[data-working-context-tooltip]').forEach(function (target) {
        const tooltipLabel = reportTitle
          ? 'Working report: ' + reportTitle
          : 'Choose working report';
        const tooltip = bootstrap.Tooltip.getInstance(target);
        if (tooltip) {
          target.setAttribute('data-bs-original-title', tooltipLabel);
          tooltip.setContent({'.tooltip-inner': tooltipLabel});
        } else {
          target.setAttribute('title', tooltipLabel);
        }
      });

      updateQuickAddControls(reportTitle);
    }

    function updateActiveReportUi(reportId, reportTitle, contextData, shouldStore) {
      const context = $.extend({}, contextData || {});
      updateActivationControls(reportId);
      updateEngagementContext(reportId, reportTitle, context);
      const stored = shouldStore === false
        ? $.extend({id: Number(reportId), title: reportTitle || ''}, context)
        : storeActiveReport(reportId, reportTitle, context);
      document.dispatchEvent(new CustomEvent('ghostwriter:working-report-changed', {
        detail: stored,
      }));
      return getActiveReportLink(reportId).length > 0;
    }

    function activateReport(url, reportId, reportTitle, csrftoken, options) {
      const activationOptions = $.extend({
        showMessage: true,
      }, options || {});
      return $.ajax({
        url: url,
        type: 'POST',
        dataType: 'json',
        data: {
          report: reportId,
        },
        beforeSend: function (xhr, ajaxSettings) {
          if (!csrfSafeMethod(ajaxSettings.type) && !this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
          }
        },
      }).done(function (data) {
        if (data.result === 'success') {
          updateActiveReportUi(reportId, data.report || reportTitle, data);
        }
        if (activationOptions.showMessage && data.message) {
          displayToastTop({
            type: data.result,
            string: data.message,
            title: 'Working Report',
            delay: 5,
          });
        }
        if (settings.redirectToShortcutAfterMessage) {
          window.setTimeout(function () {
            window.location.href = getActiveReportUrl(reportId);
          }, 5000);
        }
      }).fail(function () {
        if (!activationOptions.showMessage) {
          clearStoredActiveReport();
        }
      });
    }

    function restoreStoredActiveReport() {
      const serverContext = shellContext();
      if (serverContext && serverContext.id) {
        updateActiveReportUi(
          serverContext.id,
          serverContext.title,
          serverContext,
          true
        );
        return;
      }

      const storedReport = getStoredActiveReport();
      if (!storedReport || !storedReport.id) {
        updateQuickAddControls('');
        return;
      }

      const activationControl = getActiveReportLink(storedReport.id).get(0);
      const activationUrl = activationControl
        ? activationControl.getAttribute('activate-report-url')
        : getActivationUrl(storedReport.id);
      if (!activationUrl) {
        return;
      }
      activateReport(
        activationUrl,
        storedReport.id,
        storedReport.title,
        getCsrfToken(activationControl),
        {showMessage: false}
      );
    }

    $(document)
      .off('click.ghostwriterActiveReport', '.js-activate-report')
      .on('click.ghostwriterActiveReport', '.js-activate-report', function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();

        const reportId = this.getAttribute('activate-report-id');
        const engagement = document.querySelector('.engagement-context');
        if (
          engagement
          && String(engagement.dataset.activeReportId) === String(reportId)
        ) {
          document.dispatchEvent(new CustomEvent('ghostwriter:working-report-confirmed', {
            detail: {
              id: Number(reportId),
              title: engagement.dataset.activeReportTitle || '',
            },
          }));
          return;
        }

        activateReport(
          this.getAttribute('activate-report-url') || getActivationUrl(reportId),
          reportId,
          this.dataset.reportTitle || $.trim($(this).text()),
          getCsrfToken(this)
        );
      });

    window.addEventListener('storage', function (event) {
      if (event.key !== settings.storageKey || !event.newValue) {
        return;
      }
      try {
        const report = JSON.parse(event.newValue);
        if (report && report.id) {
          updateActiveReportUi(report.id, report.title, report, false);
        }
      } catch (error) {}
    });

    $(restoreStoredActiveReport);

    return {
      activate: activateReport,
      getStored: getStoredActiveReport,
      update: updateActiveReportUi,
    };
  }

  window.GhostwriterActiveReport = {
    init: initActiveReport,
  };
})(window, jQuery);
