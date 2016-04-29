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
require('js/koHelpers');

var GrowlBox = require('js/growlBox');

/**
 * Convenience function to create a GrowlBox
 * Show a growl-style notification for messages. Defaults to an error type.
 * @param {String} title Shows in bold at the top of the box. Required or it looks foolish.
 * @param {String} message Shows a line below the title. This could be '' if there's nothing to say.
 * @param {String} type One of 'success', 'info', 'warning', or 'danger'. Defaults to danger.
 *
 */
var growl = function(title, message, type, delay) {
    new GrowlBox(title, message, type || 'danger', delay);
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
    pathSegments.forEach(function(el){
        apiUrl.segment(el);
    });  // Hack to prevent double slashes when joining base + path
    apiUrl.query(opts.query);

    return apiUrl.toString();
};

/*
 * Perform an ajax request (cross-origin if necessary) that sends and receives JSON
 */
var ajaxJSON = function(method, url, options) {
    var defaults = {
        data: {},  // Request body (required for PUT, PATCH, POST, etc)
        isCors: false,  // Is this sending a cross-domain request? (if true, will also send any login credentials)
        fields: {}  // Additional fields (settings) for the JQuery AJAX call; overrides any defaults set by function
    };
    var opts = $.extend({}, defaults, options);

    var ajaxFields = {
        url: url,
        type: method,
        contentType: 'application/json',
        dataType: 'json'
    };
    // Add JSON payload if not a GET request
    if (method.toLowerCase() !== 'get') {
        ajaxFields.data = JSON.stringify(opts.data);
    }
    if(opts.isCors) {
        ajaxFields.crossOrigin = true;
        ajaxFields.xhrFields =  {
            withCredentials: true
        };
    }
    $.extend(true, ajaxFields, opts.fields);

    return $.ajax(ajaxFields);
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
        data: data,
        fields: {}
    };
    // For backwards compatibility. Prefer the Promise interface to these callbacks.
    if (typeof success === 'function') {
        ajaxOpts.fields.success = success;
    }
    if (typeof error === 'function') {
        ajaxOpts.fields.error = error;
    }
    return ajaxJSON('post', url, ajaxOpts);
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
        data: data,
        fields: {}
    };
    // For backwards compatibility. Prefer the Promise interface to these callbacks.
    if (typeof success === 'function') {
        ajaxOpts.fields.success = success;
    }
    if (typeof error === 'function') {
        ajaxOpts.fields.error = error;
    }
    return ajaxJSON('put', url, ajaxOpts);
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
var setXHRAuthorization = function (xhr, options) {
    if (navigator.appVersion.indexOf('MSIE 9.') === -1) {
        xhr.withCredentials = true;
        if (options) {
            options.withCredentials = true;
            options.xhrFields = {withCredentials:true};
        }
    }
    return xhr;
};

var errorDefaultShort = 'Unable to resolve';
var errorDefaultLong = 'OSF was unable to resolve your request. If this issue persists, ' +
    'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.';

var handleAddonApiHTTPError = function(error){
    var response;
    try{
        response = JSON.parse(error.response);
    } catch (e){
        response = '';
    }
    var title = response.message_short || errorDefaultShort;
    var message = response.message_long || errorDefaultLong;

    $.osf.growl(title, message);
};

var handleJSONError = function(response) {
    var title = (response.responseJSON && response.responseJSON.message_short) || errorDefaultShort;
    var message = (response.responseJSON && response.responseJSON.message_long) || errorDefaultLong;
    // We can reach this error handler when the user leaves a page while a request is pending. In that
    // case, response.status === 0, and we don't want to show an error message.
    if (response && response.status && response.status >= 400) {
        $.osf.growl(title, message);
        Raven.captureMessage('Unexpected error occurred in JSON request');
    }
};

var handleEditableError = function(response) {
    Raven.captureMessage('Unexpected error occurred in an editable input');
    return 'Error: ' + response.responseJSON.message_long;
};

var block = function(message, $element) {
    ($element ? $element.block : $.blockUI).call(
        $element || window,
        {
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
        }
    );
};

var unblock = function(element) {
    if (element) {
        $(element).unblock();
    }
    else {
        $.unblockUI();
    }
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

/**
 * A function that checks if a datestring is an ISO 8601 datetime string
 * that lacks an offset. A datetime without a time offset should default
 * to UTC according to JS standards, but Firefox implemented date parsing
 * according to the ISO spec, meaning in Firefox it will default to local
 * time
 * @param {String} dateString The original date or datetime as an ISO date/
 *                            datetime string
 */
var dateTimeWithoutOffset = function(dateString) {
    if (dateString.indexOf('T') === -1) {
        return false;
    }
    var time = dateString.split('T')[1];
    return !((time.indexOf('+') !== -1) || (time.indexOf('-') !== -1));
};

/**
 * A function that coerces a Datetime with no offset to a Datetime with
 * an offset of UTC +00 (equivalent to Z)
 * @param {String} dateTimeString The original Datetime string, which may or may not
 *                                have a terminating Z implying UTC +00
 */
var forceUTC = function(dateTimeString) {
    return dateTimeString.slice(-1) === 'Z' ? dateTimeString : dateTimeString + 'Z';
};

var hasTimeComponent = function(dateString) {
    return dateString.indexOf('T') !== -1;
};

/**
  * A date object with two formats: local time or UTC time.
  * @param {String} date The original date as a string. Should be an standard
  *                      format such as RFC or ISO. If the date is a datetime string
  *                      with no offset, an offset of UTC +00:00 will be assumed. However,
  *                      if the date is just a date (no time component), the time
  *                      component will be set to midnight local time.  Ergo, if date
  *                      is '2016-04-08' the imputed time will be '2016-04-08 04:00 UTC'
  *                      if run in EDT. But if date is '2016-04-08:00:00:00.000' it will
  *                      always be '2016-04-08 00:00 UTC', regardless of the local timezone.
  */
var LOCAL_DATEFORMAT = 'YYYY-MM-DD hh:mm A';
var UTC_DATEFORMAT = 'YYYY-MM-DD HH:mm UTC';
var FormattableDate = function(date) {

    if (typeof date === 'string') {
        this.date = moment(dateTimeWithoutOffset(date) ? forceUTC(date) : date).utc().toDate();
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


/* Responsive Affix for side nav */
var fixAffixWidth = function() {
    $('.osf-affix').each(function (){
        var el = $(this);
        var colsize = el.parent('.affix-parent').width();
        el.outerWidth(colsize);
    });
};

var initializeResponsiveAffix = function (){
    // Set nav-box width based on screem
    fixAffixWidth();
    // Show the nav box
    $('.osf-affix').each(function (){
        $(this).show();
    });
    $(window).resize(debounce(fixAffixWidth, 20, true));
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
*  Helper function to judge if the user browser is Safari
*/
var isSafari = function(userAgent) {
    userAgent = userAgent || navigator.userAgent;
    return (userAgent.search('Safari') >= 0 && userAgent.search('Chrome') < 0);
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
                className: 'btn-danger',
                callback: handleConfirmAttempt
            }
        },
        message: ''
    };

    var bootboxOptions = $.extend(true, {}, defaults, options);

    bootboxOptions.message += [
        '<p>Type the following to continue: <strong>',
        confirmationString,
        '</strong></p>',
        '<input id="bbConfirmText" class="form-control">'
    ].join('');

    bootbox.dialog(bootboxOptions);
};
/**
 * Maps an object to an array of {key: KEY, value: VALUE} pairs
 *
 * @param {Object} obj
 * @returns {Array} array of key, value pairs
 **/
var iterObject = function(obj) {
    var ret = [];
    $.each(obj, function(prop, value) {
        ret.push({
            key: prop,
            value: value
        });
    });
    return ret;
};
/** A future-proof getter for the current user
**/
var currentUser = function(){
    return window.contextVars.currentUser;
};

/**
 * Use a search function to get the index of an object in an array
 *
 * @param {Array} array
 * @param {Function} searchFn: function that returns true when an item matching the search conditions is found
 * @returns {Integer} index of matched item or -1 if no matching item is found
 **/
function indexOf(array, searchFn) {
    var len = array.length;
    for(var i = 0; i < len; i++) {
        if(searchFn(array[i])) {
            return i;
        }
    }
    return -1;
}

/**
 * Check if any of the values in an array are truthy
 *
 * @param {Array[Any]} listOfBools
 * @returns {Boolean}
 **/
var any = function(listOfBools, check) {
    var someTruthy = false;
    for(var i = 0; i < listOfBools.length; i++){
        if (check) {
            someTruthy = someTruthy || Boolean(check(listOfBools[i]));
        }
        else {
            someTruthy = someTruthy || Boolean(listOfBools[i]);
        }
        if (someTruthy) {
            return someTruthy;
        }
    }
    return false;
};

/** 
 * A helper for creating a style-guide conformant bootbox modal. Returns a promise.
 * @param {String} title: 
 * @param {String} message:
 * @param {String} actionButtonLabel:
 * @param {Object} options: optional options
 * @param {String} options.actionButtonClass: CSS class for action button, default 'btn-success'
 * @param {String} options.cancelButtonLabel: label for cancel button, default 'Cancel'
 * @param {String} options.cancelButtonClass: CSS class for cancel button, default 'btn-default'
 *
 * @example
 * dialog('Hello', 'Just saying hello', 'Say hi').done(successCallback).fail(doNothing);
 **/
var dialog = function(title, message, actionButtonLabel, options) {
    var ret = $.Deferred();
    options = $.extend({}, {
        actionButtonClass: 'btn-success',
        cancelButtonLabel: 'Cancel',
        cancelButtonClass: 'btn-default'
    }, options || {});

    bootbox.dialog({
        title: title,
        message: message,
        buttons: {
            cancel: {
                label: options.cancelButtonLabel,
                className: options.cancelButtonClass,
                callback: function() {
                    bootbox.hideAll();
                    ret.reject();
                }
            },
            approve: {
                label: actionButtonLabel,
                className: options.actionButtonClass,
                callback: ret.resolve
            }
        }
    });
    return ret.promise();
};

// Formats contributor family names for display.  Takes in project, number of contributors, and getFamilyName function
var contribNameFormat = function(node, number, getFamilyName) {
    if (number === 1) {
        return getFamilyName(0, node);
    }
    else if (number === 2) {
        return getFamilyName(0, node) + ' and ' +
            getFamilyName(1, node);
    }
    else if (number === 3) {
        return getFamilyName(0, node) + ', ' +
            getFamilyName(1, node) + ', and ' +
            getFamilyName(2, node);
    }
    else {
        return getFamilyName(0, node) + ', ' +
            getFamilyName(1, node) + ', ' +
            getFamilyName(2, node) + ' + ' + (number - 3);
    }
};

// Returns single name representing contributor, First match found of family name, given name, middle names, full name.
var findContribName = function (userAttributes) {
    var names = [userAttributes.family_name, userAttributes.given_name, userAttributes.middle_names, userAttributes.full_name];
    for (var n = 0; n < names.length; n++) {
        if (names[n]) {
            return names[n];
        }
    }
};

var trackClick = function(category, action, label){
    window.ga('send', 'event', category, action, label);
    //in order to make the href redirect work under knockout onclick binding
    return true;
};


// Call a function when scrolled to the bottom of the element
/// Useful for triggering an event at the bottom of a window, like infinite scroll
function onScrollToBottom(element, callback) {
    $(element).scroll(function() {
        var $this = $(this);
        if ($this.scrollTop() + $this.innerHeight() >= $this[0].scrollHeight) {
            callback();
        }
    });
}

// Also export these to the global namespace so that these can be used in inline
// JS. This is used on the /goodbye page at the moment.
module.exports = window.$.osf = {
    postJSON: postJSON,
    putJSON: putJSON,
    ajaxJSON: ajaxJSON,
    setXHRAuthorization: setXHRAuthorization,
    handleAddonApiHTTPError: handleAddonApiHTTPError,
    handleJSONError: handleJSONError,
    handleEditableError: handleEditableError,
    block: block,
    unblock: unblock,
    growl: growl,
    apiV2Url: apiV2Url,
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
    initializeResponsiveAffix: initializeResponsiveAffix,
    humanFileSize: humanFileSize,
    confirmDangerousAction: confirmDangerousAction,
    iterObject: iterObject,
    isIE: isIE,
    isSafari:isSafari,
    indexOf: indexOf,
    currentUser: currentUser,
    any: any,
    dialog: dialog,
    contribNameFormat: contribNameFormat,
    trackClick: trackClick,
    findContribName: findContribName,
    onScrollToBottom: onScrollToBottom
};
