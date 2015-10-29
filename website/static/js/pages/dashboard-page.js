/**
 * Initialization code for the dashboard pages.
 */

'use strict';

var Raven = require('raven-js');
var ko = require('knockout');
var $ = require('jquery');
var jstz = require('jstimezonedetect').jstz;

var $osf = require('js/osfHelpers');
var FileBrowser = require('js/file-browser.js');
var LogFeed = require('js/logFeed');
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.

var url = '/api/v1/dashboard/get_nodes/';
var request = $.getJSON(url, function(response) {
    var allNodes = response.nodes;
    //.. Getting nodes
});
request.fail(function(xhr, textStatus, error) {
    Raven.captureMessage('Could not fetch dashboard nodes.', {
        url: url, textStatus: textStatus, error: error
    });
});

var nodesListUrl = '/api/v1/dashboard/get_nodes/';

var ensureUserTimezone = function(savedTimezone, savedLocale, id) {
    var clientTimezone = jstz.determine().name();
    var clientLocale = window.navigator.userLanguage || window.navigator.language;

    if (savedTimezone !== clientTimezone || savedLocale !== clientLocale) {
        var url = '/api/v1/profile/';

        var request = $osf.putJSON(
            url,
            {
                'timezone': clientTimezone,
                'locale': clientLocale,
                'id': id
            }
        );
        request.fail(function(xhr, textStatus, error) {
            Raven.captureMessage('Could not set user timezone or locale', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    }
};

$(document).ready(function() {
    $('#projectOrganizerScope').tooltip({selector: '[data-toggle=tooltip]'});
    //var request = $.ajax({
    //    url:  'http://localhost:8000/v2/users/me/nodes',
    //    crossOrigin: true,
    //    xhrFields: { withCredentials: true}
    //});
    //request.done(function(result) {

        m.mount(document.getElementById('fileBrowser'), m.component(FileBrowser, {wrapperSelector : '#fileBrowser'}));
        // TODO: new data does not have timezone information
        //ensureUserTimezone(result.timezone, result.locale, result.id);
    //});
    //request.fail(function(xhr, textStatus, error) {
    //    Raven.captureMessage('Failed to populate user dashboard', {
    //        url: url,
    //        textStatus: textStatus,
    //        error: error
    //    });
    //});

});

