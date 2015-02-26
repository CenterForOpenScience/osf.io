'use strict';
var ko = require('knockout');
var $ = require('jquery');
require('jquery-blockui');
var Raven = require('raven-js');
var moment = require('moment');

// TODO: For some reason, this require is necessary for custom ko validators to work
// Why?!
require('koHelpers');

var GrowlBox = require('./growlBox.js');

require('bootstrap-editable');

/**
 * Convenience function to create a GrowlBox
 * Show a growl-style notification for messages. Defaults to an error type.
 * @param {String} title Shows in bold at the top of the box. Required or it looks foolish.
 * @param {String} message Shows a line below the title. This could be '' if there's nothing to say.
 * @param {String} type One of 'success', 'info', 'warning', or 'danger'. Defaults to danger.
 *
 */
var growl = function(title, message, type) {
    new GrowlBox(title, message, type);
};

/**
* Posts JSON data.
*
* NOTE: The `success` and `error` callbacks are deprecated. Prefer the Promise
* interface (using the `done` and `fail` methods of a jqXHR).
*
* Example:
*     var osf = require('./osf-helpers');
*     var request = osf.postJSON('/foo', {'email': 'bar@baz.com'});
*     request.done(function(response) {
*         // ...
*     })
*     request.fail(function(xhr, textStatus, err) {
*         // ...
*     }
*
* @param  {String} url  The url to post to
* @param  {Object} data JSON data to send to the endpoint
* @return {jQuery xhr}
*/
var postJSON = function(url, data, success, error) {
    var ajaxOpts = {
        url: url, type: 'post',
        data: JSON.stringify(data),
        contentType: 'application/json', dataType: 'json'
    };
    // For backwards compatibility. Prefer the Promise interface to these callbacks.
    if (typeof success === 'function') {
        ajaxOpts.success = success;
    }
    if (typeof error === 'function') {
        ajaxOpts.error = error;
    }
    return $.ajax(ajaxOpts);
};

/**
  * Puts JSON data.
  *
  * NOTE: The `success` and `error` callbacks are deprecated. Prefer the Promise
  * interface (using the `done` and `fail` methods of a jqXHR).
  *
  * Example:
  *     osf.putJSON('/foo', {'email': 'bar@baz.com'})
  *
  * @param  {String} url  The url to put to
  * @param  {Object} data JSON data to send to the endpoint
  * @return {jQuery xhr}
  */
var putJSON = function(url, data, success, error) {
    var ajaxOpts = {
        url: url, type: 'put',
        data: JSON.stringify(data),
        contentType: 'application/json', dataType: 'json'
    };
    // For backwards compatibility. Prefer the Promise interface to these callbacks.
    if (typeof success === 'function') {
        ajaxOpts.success = success;
    }
    if (typeof error === 'function') {
        ajaxOpts.error = error;
    }
    return $.ajax(ajaxOpts);
};

var errorDefaultShort = 'Unable to resolve';
var errorDefaultLong = 'OSF was unable to resolve your request. If this issue persists, ' +
    'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.';

var handleJSONError = function(response) {
    var title = response.responseJSON.message_short || errorDefaultShort;
    var message = response.responseJSON.message_long || errorDefaultLong;

    $.osf.growl(title, message);

    Raven.captureMessage('Unexpected error occurred in JSON request');
};

var handleEditableError = function(response) {
    Raven.captureMessage('Unexpected error occurred in an editable input');
    return 'Unexpected error: ' + response.statusText;
};

var block = function() {
    $.blockUI({
        css: {
            border: 'none',
            padding: '15px',
            backgroundColor: '#000',
            '-webkit-border-radius': '10px',
            '-moz-border-radius': '10px',
            opacity: 0.5,
            color: '#fff'
        },
        message: 'Please wait'
    });
};

var unblock = function() {
    $.unblockUI();
};

var joinPrompts = function(prompts, base) {
    var prompt = base || '';
    if (prompts.length !==0) {
        prompt += '<hr />';
        prompt += '<ul>';
        for (var i=0; i<prompts.length; i++) {
            prompt += '<li>' + prompts[i] + '</li>';
        }
        prompt += '</ul>';
    }
    return prompt;
};

var mapByProperty = function(list, attr) {
    return $.map(list, function(item) {
        return item[attr];
    });
};


/**
  * Return whether or not a value is an email address.
  * Adapted from Knockout-Validation.
  */
var isEmail = function(value) {
    return  /^((([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))$/i.test(value);
};

/**
  * Get query string arguments as an object.
  * From getQueryParameters plugin by Nicholas Ortenzio.
  *
  */
var urlParams = function(str) {
    return (str || document.location.search).replace(/(^\?)/,'').split('&')
        .map(function(n){return n = n.split('='),this[n[0]] = decodeURIComponent(n[1]).replace(/\+/g, ' '),this;}.bind({}))[0];
};


/**
 * From Underscore.js, MIT License
 *
 * Returns a function, that, when invoked, will only be triggered at most once
 * during a given window of time. Normally, the throttled function will run
 * as much as it can, without ever going more than once per `wait` duration;
 * but if you'd like to disable the execution on the leading edge, pass
 * `{leading: false}`. To disable execution on the trailing edge, ditto.
 */
var throttle = function(func, wait, options) {
    var context, args, result;
    var timeout = null;
    var previous = 0;
    if (!options) {
        options = {};
    }
    var later = function() {
        previous = options.leading === false ? 0 : new Date().getTime();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout) {
            context = args = null;
        }
    };
    return function() {
        var now = new Date().getTime();
        if (!previous && options.leading === false) {
            previous = now;
        }
            var remaining = wait - (now - previous);
            context = this;
            args = arguments;
            if (remaining <= 0 || remaining > wait) {
            clearTimeout(timeout);
            timeout = null;
            previous = now;
            result = func.apply(context, args);
            if (!timeout) {
                context = args = null;
            }
        } else if (!timeout && options.trailing !== false) {
            timeout = setTimeout(later, remaining);
        }
        return result;
    };
};

// From Underscore.js, MIT License
//
// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.

var debounce = function(func, wait, immediate) {
  var timeout, args, context, timestamp, result;

  var later = function() {
    var last = new Date().getTime() - timestamp;

    if (last < wait && last >= 0) {
      timeout = setTimeout(later, wait - last);
    } else {
      timeout = null;
      if (!immediate) {
        result = func.apply(context, args);
        if (!timeout) {
            context = args = null;
        }
      }
    }
  };

  return function() {
    context = this;
    args = arguments;
    timestamp = new Date().getTime();
    var callNow = immediate && !timeout;
    if (!timeout) {
        timeout = setTimeout(later, wait);
    }
    if (callNow) {
      result = func.apply(context, args);
      context = args = null;
    }

    return result;
  };
};

///////////
// Piwik //
///////////

var trackPiwik = function(host, siteId, cvars, useCookies) {
    cvars = Array.isArray(cvars) ? cvars : [];
    useCookies = typeof(useCookies) !== 'undefined' ? useCookies : false;
    try {
        var piwikTracker = window.Piwik.getTracker(host + 'piwik.php', siteId);
        piwikTracker.enableLinkTracking(true);
        for(var i=0; i<cvars.length;i++)
        {
            piwikTracker.setCustomVariable.apply(null, cvars[i]);
        }
        if (!useCookies) {
            piwikTracker.disableCookies();
        }
        piwikTracker.trackPageView();

    } catch(err) { return false; }
    return true;
};

//////////////////
// Data binders //
//////////////////

/**
 * Tooltip data binder. The value accessor should be an object containing
 * parameters for the tooltip.
 * Example:
 * <span data-bind="tooltip: {title: 'Tooltip text here'}"></span>
 */
ko.bindingHandlers.tooltip = {
    init: function(elem, valueAccessor) {
        $(elem).tooltip(valueAccessor());
    }
};

/**
  * A thin wrapper around ko.applyBindings that ensures that a view model
  * is bound to the expected element. Also shows the element if it was
  * previously hidden.
  *
  * Takes a ViewModel and a selector (String).
  */
var applyBindings = function(viewModel, selector) {
    var $elem = $(selector);
    if ($elem.length === 0) {
        throw "No elements matching selector '" + selector + "'";  // jshint ignore: line
    }
    if ($elem.length > 1) {
        throw "Can't bind ViewModel to multiple elements."; // jshint ignore: line
    }
    // Ensure that the bound element is shown
    if ($elem.hasClass('scripted')){
        $elem.show();
    }
    ko.applyBindings(viewModel, $elem[0]);
};


/**
  * A date object with two formats: local time or UTC time.
  * @param {String} date The original date as a string. Should be an standard
  *                      format such as RFC or ISO.
  */
var LOCAL_DATEFORMAT = 'YYYY-MM-DD hh:mm A';
var UTC_DATEFORMAT = 'YYYY-MM-DD HH:mm UTC';
var FormattableDate = function(date) {
    if (typeof date === 'string') {
        // The date as a Date object
        this.date = new Date(date);
    } else {
        this.date = date;
    }
    this.local = moment(this.date).format(LOCAL_DATEFORMAT);
    this.utc = moment.utc(this.date).format(UTC_DATEFORMAT);
};

/**
 * Escapes html characters in a string.
 */
var htmlEscape = function(text) {
    return $('<div/>').text(text).html();
};

// Also export these to the global namespace so that these can be used in inline
// JS. This is used on the /goodbye page at the moment.
module.exports = window.$.osf = {
    postJSON: postJSON,
    putJSON: putJSON,
    handleJSONError: handleJSONError,
    handleEditableError: handleEditableError,
    block: block,
    growl: growl,
    unblock: unblock,
    joinPrompts: joinPrompts,
    mapByProperty: mapByProperty,
    isEmail: isEmail,
    urlParams: urlParams,
    trackPiwik: trackPiwik,
    applyBindings: applyBindings,
    FormattableDate: FormattableDate,
    throttle: throttle,
    debounce: debounce,
    htmlEscape: htmlEscape
};
