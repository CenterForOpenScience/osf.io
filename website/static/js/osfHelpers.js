'use strict';
var ko = require('knockout');
var $ = require('jquery');
require('jquery-blockui');
var Raven = require('raven-js');
var moment = require('moment');
var URI = require('URIjs');
var bootbox = require('bootbox');
var iconmap = require('js/iconmap');

// TODO: For some reason, this require is necessary for custom ko validators to work
// Why?!
require('./koHelpers');

var GrowlBox = require('js/growlBox');

/**
 * Convenience function to create a GrowlBox
 * Show a growl-style notification for messages. Defaults to an error type.
 * @param {String} title Shows in bold at the top of the box. Required or it looks foolish.
 * @param {String} message Shows a line below the title. This could be '' if there's nothing to say.
 * @param {String} type One of 'success', 'info', 'warning', or 'danger'. Defaults to danger.
 *
 */
var growl = function(title, message, type) {
    new GrowlBox(title, message, type || 'danger');
};


/**
 * Generate OSF absolute URLs, including prefix and arguments. Assumes access to mako globals for pieces of URL.
 * Can optionally pass in an object with params (name:value) to be appended to URL. Calling as:
 *   apiV2Url('users/4urxt/applications',
 *      {query:
 *          {'a':1, 'filter[fullname]': 'lawrence'},
 *       prefix: 'https://staging2.osf.io/api/v2/'})
 * would yield the result:
 *  'https://staging2.osf.io/api/v2/users/4urxt/applications?a=1&filter%5Bfullname%5D=lawrence'
 * @param {String} path The string to be appended to the absolute base path, eg 'users/4urxt'
 * @param {Object} options (optional)
 */
var apiV2Url = function (path, options){
    var contextVars = window.contextVars || {};
    var defaultPrefix = contextVars.apiV2Prefix || '';

    var defaults = {
        prefix: defaultPrefix, // Manually specify the prefix for API routes (useful for testing)
        query: {}  // Optional query parameters to be appended to URL
    };
    var opts = $.extend({}, defaults, options);

    var apiUrl = URI(opts.prefix);
    var pathSegments = URI(path).segment();
    pathSegments.forEach(function(el){apiUrl.segment(el);});  // Hack to prevent double slashes when joining base + path
    apiUrl.query(opts.query);

    return apiUrl.toString();
};


/**
* Posts JSON data.
*
* NOTE: The `success` and `error` callbacks are deprecated. Prefer the Promise
* interface (using the `done` and `fail` methods of a jqXHR).
*
* Example:
*     var $osf = require('./osf-helpers');
*     var request = $osf.postJSON('/foo', {'email': 'bar@baz.com'});
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

/**
* Set XHR Authentication
*
* Example:
*     var $osf = require('./osf-helpers');
*
*     JQuery
*     $ajax({
*         beforeSend: $osf.setXHRAuthorization,
*         // ...
*     }).done( ... );
*
*     MithrilJS
*     m.request({
*         config: $osf.setXHRAuthorization,
*         // ...
*     }).then( ... );
*
* @param  {Object} XML Http Request
* @return {Object} xhr
*/
var setXHRAuthorization = function (xhr) {
    if (window.contextVars.accessToken) {
        xhr.setRequestHeader('Authorization', 'Bearer ' + window.contextVars.accessToken);
    }
    return xhr;
};

var errorDefaultShort = 'Unable to resolve';
var errorDefaultLong = 'OSF was unable to resolve your request. If this issue persists, ' +
    'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.';

var handleJSONError = function(response) {
    var title = (response.responseJSON && response.responseJSON.message_short) || errorDefaultShort;
    var message = (response.responseJSON && response.responseJSON.message_long) || errorDefaultLong;

    $.osf.growl(title, message);

    Raven.captureMessage('Unexpected error occurred in JSON request');
};

var handleEditableError = function(response) {
    Raven.captureMessage('Unexpected error occurred in an editable input');
    return 'Unexpected error: ' + response.statusText;
};

var block = function(message) {
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
        message: message || 'Please wait'
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
  * If `str` is falsy, return {}.
  * Modified from getQueryParameters plugin by Nicholas Ortenzio (MIT Licensed).
  */
var urlParams = function(str) {
    var stringToParse = str || document.location.search;
    if (!stringToParse) {
        return {};
    }
    return (stringToParse).replace(/(^\?)/,'').split('&')
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
 * <span data-bind='tooltip: {title: 'Tooltip text here'}'></span>
 */
ko.bindingHandlers.tooltip = {
    init: function(elem, valueAccessor) {
        $(elem).tooltip(valueAccessor());
    }
};


/**
 * Takes over anchor scrolling and scrolls to anchor positions within elements
 * Example:
 * <span data-bind='anchorScroll'></span>
 */
ko.bindingHandlers.anchorScroll = {
    init: function(elem, valueAccessor) {
        var buffer = valueAccessor().buffer || 100;
        var element = valueAccessor().elem || elem;
        var offset;
        $(element).on('click', 'a[href^="#"]', function (event) {
            var $item = $(this);
            var $element = $(element);
            if(!$item.attr('data-model') && $item.attr('href') !== '#') {
                event.preventDefault();
                // get location of the target
                var target = $item.attr('href');
                // if target has a scrollbar scroll it, otherwise scroll the page
                if ( $element.get(0).scrollHeight > $element.height() ) {
                    offset = $(target).position();
                    $element.scrollTop(offset.top - buffer);
                } else {
                    offset = $(target).offset();
                    $(window).scrollTop(offset.top - 100); // This is fixed to 100 because of the fixed navigation menus on the page
                }
            }
        });
    }
};

/**
 * Adds class returned from iconmap to the element. The value accessor should be the
 * category of the node.
 * Example:
 * <span data-bind="getIcon: 'analysis'"></span>
 */
ko.bindingHandlers.getIcon = {
    init: function(elem, valueAccessor) {
        var icon;
        var category = valueAccessor();
        if (Object.keys(iconmap.componentIcons).indexOf(category) >=0 ){
            icon = iconmap.componentIcons[category];
        }
        else {
            icon = iconmap.projectIcons[category];
        }
        $(elem).addClass(icon);
    }
};

/**
 * Required in render_node.mako to call getIcon. As a result of modularity there
 * are overlapping scopes. To temporarily escape the parent scope and allow other binding
 * stopBinding can be used. Only other option was to redo the structure of the scopes.
 * Example:
 * <span data-bind="stopBinding: true"></span>
 */
ko.bindingHandlers.stopBinding = {
    init: function() {
        return { controlsDescendantBindings: true };
    }
};

/**
 * Allows data-bind to be called without a div so the layout of the page is not effected.
 * Example:
 * <!-- ko stopBinding: true -->
 */
ko.virtualElements.allowedBindings.stopBinding = true;

/**
  * A thin wrapper around ko.applyBindings that ensures that a view model
  * is bound to the expected element. Also shows the element (and child elements) if it was
  * previously hidden by applying the 'scripted' CSS class.
  *
  * Takes a ViewModel and a selector (string) or a DOM element.
  */
var applyBindings = function(viewModel, selector) {
    var elem, cssSelector;
    var $elem = $(selector);
    if (typeof(selector.nodeName) === 'string') { // dom element
        elem = selector;
        // NOTE: Only works with DOM elements that have an ID
        cssSelector = '#' + elem.id;
    } else {
        elem = $elem[0];
        cssSelector = selector;
    }
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
    // Also show any child elements that have the scripted class
    $(cssSelector + ' .scripted').each(function(elm) {
        $(this).show();
    });
    ko.applyBindings(viewModel, $elem[0]);
};


var hasTimeComponent = function(dateString) {
    return dateString.indexOf('T') !== -1;
};

var forceUTC = function(dateTimeString) {
    return dateTimeString.slice(-1) === 'Z' ? dateTimeString : dateTimeString + 'Z';
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
        this.date = new Date(hasTimeComponent(date) ? forceUTC(date) : date);
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


/**
 * Decode Escaped html characters in a string.
 */
var htmlDecode = function(text) {
    return $('<div/>').html(text).text();
};

/**
+ * Resize table to match thead and tbody column
+ */

var tableResize = function(selector, checker) {
    // Change the selector if needed
    var $table = $(selector);
    var $bodyCells = $table.find('tbody tr:first').children();
    var colWidth;

    // Adjust the width of thead cells when window resizes
    $(window).resize(function() {
        // Get the tbody columns width array
        colWidth = $bodyCells.map(function() {
            return $(this).width();
        }).get();
        // Set the width of thead columns
        $table.find('thead tr').children().each(function(i, v) {
            if(i === 0 && $(v).width() > colWidth[i]){
                $($bodyCells[i]).width($(v).width());
            }
            if(checker && i === checker) {
                $(v).width(colWidth[i] + colWidth[i + 1]);
            }else{
                $(v).width(colWidth[i]);
            }
        });
    }).resize(); // Trigger resize handler
};

/* A binding handler to convert lists into formatted lists, e.g.:
 * [dog] -> dog
 * [dog, cat] -> dog and cat
 * [dog, cat, fish] -> dog, cat, and fish
 *
 * This handler should not be used for user inputs.
 *
 * Example use:
 * <span data-bind="listing: {data: ['Alpha', 'Beta', 'Gamma'],
 *                            map: function(item) {return item.charAt(0) + '.';}}"></span>
 * yields
 * <span ...>A., B., and G.</span>
 */
ko.bindingHandlers.listing = {
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var value = valueAccessor();
        var valueUnwrapped = ko.unwrap(value);
        var map = valueUnwrapped.map || function(item) {return item;};
        var data = valueUnwrapped.data || [];
        var keys = [];
        if (!Array.isArray(data)) {
            keys = Object.keys(data);
        }
        else {
            keys = data;
        }
        var index = 1;
        var list = ko.utils.arrayMap(keys, function(key) {
            var ret;
            if (index === 1){
                ret = '';
            }
            else if (index === 2){
                if (valueUnwrapped.length === 2) {
                    ret = ' and ';
                }
                else {
                    ret = ', ';
                }
            }
            else {
                ret = ', and ';
            }
            ret += map(key, data[key]);
            index++;
            return ret;
        }).join('');
        $(element).html(list);
    }
};

// Thanks to https://stackoverflow.com/questions/10420352/converting-file-size-in-bytes-to-human-readable
function humanFileSize(bytes, si) {
    var thresh = si ? 1000 : 1024;
    if(Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    var units = si ?
        ['kB','MB','GB','TB','PB','EB','ZB','YB'] :
        ['KiB','MiB','GiB','TiB','PiB','EiB','ZiB','YiB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while(Math.abs(bytes) >= thresh && u < units.length - 1);
    return bytes.toFixed(1) + ' ' + units[u];
}

/**
*  returns a random name from this list to use as a confirmation string
*/
var _confirmationString = function() {
    // TODO: Generate a random string here instead of using pre-set values
    //       per Jeff, use ~10 characters
    var scientists = [
        'Anning',
        'Banneker',
        'Cannon',
        'Carver',
        'Chappelle',
        'Curie',
        'Divine',
        'Emeagwali',
        'Fahlberg',
        'Forssmann',
        'Franklin',
        'Herschel',
        'Hodgkin',
        'Hopper',
        'Horowitz',
        'Jemison',
        'Julian',
        'Kovalevsky',
        'Lamarr',
        'Lavoisier',
        'Lovelace',
        'Massie',
        'McClintock',
        'Meitner',
        'Mitchell',
        'Morgan',
        'Odum',
        'Pasteur',
        'Pauling',
        'Payne',
        'Pearce',
        'Pollack',
        'Rillieux',
        'Sanger',
        'Somerville',
        'Tesla',
        'Tyson',
        'Turing'
    ];

    return scientists[Math.floor(Math.random() * scientists.length)];
};

/**
*  Helper function to judge if the user browser is IE
*/
var isIE = function(userAgent) {
    userAgent = userAgent || navigator.userAgent;
    return userAgent.indexOf('MSIE ') > -1 || userAgent.indexOf('Trident/') > -1;
};

/**
  * Confirm a dangerous action by requiring the user to enter specific text
  *
  * This is an abstraction over bootbox, and passes most options through to
  * bootbox.dailog(). The exception to this is `callback`, which is called only
  * if the user correctly confirms the action.
  *
  * @param  {Object} options
  */
var confirmDangerousAction = function (options) {
    // TODO: Refactor this to be more interactive - use a ten-key-like interface
    //       and display one character at a time for the user to enter. Once
    //       they enter that character, display another. This will require more
    //       sustained attention and will prevent the user from copy/pasting a
    //       random string.

    var confirmationString = _confirmationString();

    // keep the users' callback for re-use; we'll pass ours to bootbox
    var callback = options.callback;
    delete options.callback;

    // this is our callback
    var handleConfirmAttempt = function () {
        var verified = ($('#bbConfirmText').val() === confirmationString);

        if (verified) {
            callback();
        } else {
            growl('Verification failed', 'Strings did not match');
        }
    };

    var defaults = {
        title: 'Confirm action',
        confirmText: confirmationString,
        buttons: {
            cancel: {
                label: 'Cancel',
                className: 'btn-default'
            },
            success: {
                label: 'Confirm',
                className: 'btn-success',
                callback: handleConfirmAttempt
            }
        },
        message: ''
    };

    var bootboxOptions = $.extend({}, defaults, options);

    bootboxOptions.message += [
        '<p>Type the following to continue: <strong>',
        confirmationString,
        '</strong></p>',
        '<input id="bbConfirmText" class="form-control">'
    ].join('');

    bootbox.dialog(bootboxOptions);
};

// Also export these to the global namespace so that these can be used in inline
// JS. This is used on the /goodbye page at the moment.
module.exports = window.$.osf = {
    postJSON: postJSON,
    putJSON: putJSON,
    setXHRAuthorization: setXHRAuthorization,
    handleJSONError: handleJSONError,
    handleEditableError: handleEditableError,
    block: block,
    growl: growl,
    apiV2Url: apiV2Url,
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
    htmlEscape: htmlEscape,
    htmlDecode: htmlDecode,
    tableResize: tableResize,
    humanFileSize: humanFileSize,
    confirmDangerousAction: confirmDangerousAction,
    isIE: isIE
};
