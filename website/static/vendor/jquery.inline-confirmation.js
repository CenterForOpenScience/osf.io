/**
 * Inline Confirmation plugin for jQuery
 *
 * One of the less obtrusive ways of implementing a confirmation dialogue. Requires jQuery 1.7+.
 *
 * v1.4.2
 *
 * Copyright (c) 2010 Fred Wu
 *
 * Released under the MIT license: http://www.opensource.org/licenses/mit-license.php
 */

/**
 * Usage:
 *
 * // using default options
 * $("a.delete").inlineConfirmation();
 *
 * // using some custom options
 * $("a.delete").inlineConfirmation({
 *   confirm: "<a href='#' class='confirm-yes'>Yes</a>",
 *   cancel: "<a href='#' class='confirm-no'>No</a>",
 *   separator: " | ",
 *   reverse: true,
 *   bindsOnEvent: "hover",
 *   confirmCallback: function(action) {
 *     action.parent().fadeIn();
 *   }
 * });
 *
 * Configuration options:
 *
 * confirm            string    the HTML for the confirm action (default: "<a href='#'>Confirm</a>")
 * cancel             string    the HTML for the cancel action (default: "<a href='#'>Cancel</a>")
 * separator          string    the HTML for the separator between the confirm and the cancel actions (default: " ")
 * reverse            boolean   revert the confirm and the cancel actions (default: false)
 * hideOriginalAction boolean   whether or not to hide the original action, useful for display the dialogue as a modal if set to false (default: true)
 * bindsOnEvent       string    the JavaScript event handler for binding the confirmation action (default: "click")
 * expiresIn          integer   seconds before the confirmation dialogue closes automatically, 0 to disable this feature (default: 0)
 * confirmCallback    function  the callback function to execute after the confirm action, accepts the original action object as an argument
 * cancelCallback     function  the callback function to execute after the cancel action, accepts the original action object as an argument
 */

(function($){

  $.fn.inlineConfirmation = function(options) {
    var defaults = {
      confirm: "<a href='#'>Confirm</a>",
      cancel: "<a href='#'>Cancel</a>",
      separator: " ",
      reverse: false,
      hideOriginalAction: true,
      bindsOnEvent: "click",
      expiresIn: 0,
      confirmCallback: function() { return true; },
      cancelCallback: function() { return true; }
    };

    var original_action;
    var timeout_id;
    var all_actions     = $(this);
    var options         = $.extend(defaults, options);
    var block_class     = "inline-confirmation-block";
    var confirm_class   = "inline-confirmation-confirm";
    var cancel_class    = "inline-confirmation-cancel";
    var action_class    = "inline-confirmation-action";

    options.confirm = "<span class='" + action_class + " " + confirm_class + "'>" + options.confirm + "</span>";
    options.cancel  = "<span class='" + action_class + " " + cancel_class + "'>" + options.cancel + "</span>";

    var action_set = options.reverse === false
      ? options.confirm + options.separator + options.cancel
      : options.cancel + options.separator + options.confirm;

    $(this).on(options.bindsOnEvent, function(e) {
      original_action = $(this);

      all_actions.show();
      $("span." + block_class).hide();

      if (options.hideOriginalAction === true) {
        $(this).trigger("update").hide();
      }

      var active_action_set = $("span." + block_class, $(this).parent());

      if (active_action_set.length > 0) {
        active_action_set.show();
      } else {
        $(this).after("<span class='" + block_class + "'>" + action_set + "</span>");
      }

      if (options.expiresIn > 0) {
        timeout_id = setTimeout(function() {
          $("span." + block_class, original_action.parent()).hide();
          original_action.show();
        }, options.expiresIn * 1000);
      }

      e.preventDefault();
      return false;
    });

    $(this).parent().delegate("span." + action_class, "click", function() {
      clearTimeout(timeout_id);
      $(this).parent().hide();
      original_action.show();

      var args = new Array();
      args[0]  = original_action;

      if ($(this).hasClass(confirm_class)) {
        options.confirmCallback.apply(this, args);
      } else {
        options.cancelCallback.apply(this, args);
      }
      return false;
    });
  };

})(jQuery);
