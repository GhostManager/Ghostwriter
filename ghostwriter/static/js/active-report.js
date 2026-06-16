(function (window, $) {
  const DEFAULT_STORAGE_KEY = 'ghostwriter-active-report';

  function initActiveReport(options) {
    const settings = $.extend({
      storageKey: DEFAULT_STORAGE_KEY,
      reportUrlTemplate: '',
      redirectToShortcutAfterMessage: false,
    }, options || {});

    function getActiveReportUrl(reportId) {
      return settings.reportUrlTemplate.replace('0', reportId);
    }

    function getActiveReportLink(reportId) {
      return $('.js-activate-report[activate-report-id="' + reportId + '"]').first();
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

    function storeActiveReport(reportId, reportTitle) {
      try {
        localStorage.setItem(settings.storageKey, JSON.stringify({
          id: reportId,
          title: reportTitle || '',
        }));
      } catch (error) {}
    }

    function clearStoredActiveReport() {
      try {
        localStorage.removeItem(settings.storageKey);
      } catch (error) {}
    }

    function updateActiveReportUi(reportId, reportTitle) {
      const reportLink = getActiveReportLink(reportId);
      if (!reportLink.length) {
        return false;
      }

      $('.empty-report').addClass('selected-report').toggleClass('empty-report');
      $('.js-activate-report').removeClass('selected-report toggle-on-icon').addClass('toggle-off-icon');
      reportLink.addClass('selected-report toggle-on-icon').removeClass('toggle-off-icon');
      $('.active-report-shortcut')
        .attr('href', getActiveReportUrl(reportId))
        .text('Jump to Report')
        .removeClass('btn-disabled');
      storeActiveReport(reportId, reportTitle || $.trim(reportLink.text()));
      return true;
    }

    function restoreStoredActiveReport() {
      const selectedReport = $('.js-activate-report.selected-report').first();
      if (selectedReport.length) {
        updateActiveReportUi(
          selectedReport.attr('activate-report-id'),
          $.trim(selectedReport.text())
        );
        return;
      }

      const storedReport = getStoredActiveReport();
      if (!storedReport || !storedReport.id) {
        return;
      }

      const reportLink = getActiveReportLink(storedReport.id);
      if (!reportLink.length) {
        return;
      }

      updateActiveReportUi(storedReport.id, storedReport.title);
      $.ajax({
        url: reportLink.attr('activate-report-url'),
        type: 'POST',
        dataType: 'json',
        data: {
          'report': storedReport.id,
        },
        beforeSend: function (xhr, ajaxSettings) {
          if (!csrfSafeMethod(ajaxSettings.type) && !this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', reportLink.attr('activate-report-csrftoken'));
          }
        },
        success: function (data) {
          if (data['result'] === 'success') {
            updateActiveReportUi(storedReport.id, data['report']);
          } else {
            clearStoredActiveReport();
          }
        },
        error: clearStoredActiveReport,
      });
    }

    $('.js-activate-report').click(function (e) {
      let url = $(this).attr('activate-report-url');
      let reportId = $(this).attr('activate-report-id');
      let csrftoken = $(this).attr('activate-report-csrftoken');
      let shortcutUrl = getActiveReportUrl(reportId);
      $.ajaxSetup({
        beforeSend: function (xhr, ajaxSettings) {
          if (!csrfSafeMethod(ajaxSettings.type) && !this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', csrftoken);
          }
        },
      });
      $.ajax({
        url: url,
        type: 'POST',
        dataType: 'json',
        data: {
          'report': reportId,
        },
        success: function (data) {
          if (data['result'] === 'success') {
            updateActiveReportUi(reportId, data['report']);
          }
          if (data['message']) {
            displayToastTop({type: data['result'], string: data['message'], title: 'Report Update', delay: 5});
            if (settings.redirectToShortcutAfterMessage) {
              setTimeout(function () {
                window.location.href = shortcutUrl;
              }, 5000);
            }
          }
        },
      });
      e.stopImmediatePropagation();
    });

    $(restoreStoredActiveReport);
  }

  window.GhostwriterActiveReport = {
    init: initActiveReport,
  };
})(window, jQuery);
