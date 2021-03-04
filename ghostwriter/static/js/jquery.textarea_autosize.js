/*!
 * jQuery Textarea AutoSize plugin
 * Author: Javier Julio
 * Licensed under the MIT license
 */

 // https://github.com/javierjulio/textarea-autosize

;(function ($, window, document, undefined) {

    var pluginName = "textareaAutoSize";
    var pluginDataName = "plugin_" + pluginName;

    var containsText = function (value) {
      return (value.replace(/\s/g, '').length > 0);
    };

    function Plugin(element, options) {
      this.element = element;
      this.$element = $(element);
      this.init();
    }

    Plugin.prototype = {
      init: function() {
        var diff = parseInt(this.$element.css('paddingBottom')) +
                   parseInt(this.$element.css('paddingTop')) +
                   parseInt(this.$element.css('borderTopWidth')) +
                   parseInt(this.$element.css('borderBottomWidth')) || 0;

        if (containsText(this.element.value)) {
          this.$element.height(this.element.scrollHeight - diff);
        }

        // keyup is required for IE to properly reset height when deleting text
        this.$element.on('input keyup', function(event) {
          var $window = $(window);
          var currentScrollPosition = $window.scrollTop();

          $(this)
            .height(0)
            .height(this.scrollHeight - diff);

          $window.scrollTop(currentScrollPosition);
        });
      }
    };

    $.fn[pluginName] = function (options) {
      this.each(function() {
        if (!$.data(this, pluginDataName)) {
          $.data(this, pluginDataName, new Plugin(this, options));
        }
      });
      return this;
    };

  })(jQuery, window, document);