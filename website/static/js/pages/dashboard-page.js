/**
 * Initialization code for the dashboard pages.
 */

'use strict';

var Raven = require('raven-js');
var ko = require('knockout');
var $ = require('jquery');
var jstz = require('jstimezonedetect').jstz;

var $osf = require('js/osfHelpers');
var LogFeed = require('js/logFeed');
var ProjectOrganizer = require('js/projectorganizer').ProjectOrganizer;

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

    var request = $.ajax({
        url:  '/api/v1/dashboard/'
    });
    request.done(function(data) {
        //var po = new ProjectOrganizer({
        //    placement : 'dashboard',
        //    divID: 'project-grid',
        //    filesData: data.data,
        //    multiselect : true
        //});

        ensureUserTimezone(data.timezone, data.locale, data.id);
    });
    request.fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Failed to populate user dashboard', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });

});

