'use strict';

var Raven = require('raven-js');
var URI = require('URIjs');
var oop = require('js/oop');
var $ = require('jquery');

var DOMAIN = '';

var BaseClient = oop.defclass({
    PREFIX: '/api',
    DEFAULT_AJAX_OPTIONS: {
        contentType: 'application/json',
        dataType: 'json'
    },
    constructor: function() {},
    /**
     * Make an API request.
     * NOTE: Assumes request bodies are JSON.
     *
     * @param {object} params
     *  {string} method
     *  {string} url
     *  {object} query
     *  {object} data: Request body (will be JSONified)
     *  {object} options: Additional options to pass to $.ajax
     */
    _request: function(params) {
        var baseUrl = DOMAIN + this.PREFIX + params.url;
        var uri = URI(baseUrl)
            .query(params.query || {}).toString();
        var jsonData = JSON.stringify(params.data || {});
        console.log(uri);
        var opts = $.extend(
            {},
            {url: uri, data: jsonData, type: params.method || 'GET'}, this.DEFAULT_AJAX_OPTIONS,
            params.options
        );
        return $.ajax(opts);
    }
});

/**
 * Return a generic error handler for requests.
 * Log to Sentry with the given message.
 *
 * Usage:
 *     client.makeRequest()
 *          .fail(captureError('Failed to make request'));
 */
var DEFAULT_ERROR_MESSAGE = 'Request failed.';
function captureError(message, callback) {
    return function(xhr, status, error) {
        Raven.captureMessage(message || DEFAULT_ERROR_MESSAGE, {
            extra: { xhr: xhr, status: status, error: error }
        });
        // Additional error-handling
        callback && callback(xhr, status, error);
    };
}

module.exports = {
    BaseClient: BaseClient,
    captureError: captureError
};
