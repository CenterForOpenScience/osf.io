'use strict';
var $ = require('jquery');

/* Send with ajax calls to work with api2 */
var apiV2Config = function (options) {
    var defaults = {
        withCredentials: true
    }
    var opts = $.extend({}, defaults, options);
    return function (xhr) {
        xhr.withCredentials = opts.withCredentials;
        xhr.setRequestHeader('Content-Type', 'application/vnd.api+json;');
        xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');
    };
};

var unwrap = function (value) {
    return typeof(value) === 'function' ? value() : value;
};

module.exports = {
    apiV2Config: apiV2Config,
    unwrap: unwrap
};
