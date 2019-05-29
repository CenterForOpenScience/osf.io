'use strict';
var $ = require('jquery');
var Cookie = require('js-cookie');
var iconmap = require('js/iconmap').projectComponentIcons;
var m = require('mithril');

/* Send with ajax calls to work with api2 */
var apiV2Config = function (options) {
    var defaults = {
        withCredentials: true
    };
    var opts = $.extend({}, defaults, options);
    return function (xhr, params) {
        xhr.withCredentials = opts.withCredentials;
        xhr.setRequestHeader('Content-Type', 'application/vnd.api+json;');
        xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
        var url = params.url;
        // Add X-CSRFToken to v2 requests
        if (params.method !== 'GET' &&
            window.contextVars &&
            window.contextVars.csrfCookieName &&
            window.contextVars.apiV2Domain &&
            url.match(new RegExp('^' + window.contextVars.apiV2Domain))) {
            var csrfToken = Cookie.get(window.contextVars.csrfCookieName);
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
        }
    };
};

var unwrap = function (value) {
    return typeof(value) === 'function' ? value() : value;
};

var getIcon = function (category) {
    if (iconmap.hasOwnProperty(category)){
      return iconmap[category];
    }
    return '';
};

module.exports = {
    apiV2Config: apiV2Config,
    getIcon: getIcon,
    unwrap: unwrap
};
