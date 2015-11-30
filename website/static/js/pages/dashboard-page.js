/**
 * Initialization code for the dashboard pages. Starts up the Project Organizer
 * and binds the onboarder Knockout components.
 */

'use strict';

var Raven = require('raven-js');
var ko = require('knockout');
var $ = require('jquery');
var jstz = require('jstimezonedetect');

// Knockout components for the onboarder
require('js/onboarder.js');
var $osf = require('js/osfHelpers');
var LogFeed = require('js/logFeed');
var ProjectOrganizer = require('js/projectorganizer').ProjectOrganizer;

var url = '/api/v1/dashboard/get_nodes/';
var request = $.getJSON(url, function(response) {
    var allNodes = response.nodes;
    //  For uploads, only show nodes for which user has write or admin permissions
    var uploadSelection = ko.utils.arrayFilter(allNodes, function(node) {
        return $.inArray(node.permissions, ['write', 'admin']) !== -1;
    });

    // If we need to change what nodes can be registered, filter here
    var registrationSelection = ko.utils.arrayFilter(allNodes, function(node) {
        return $.inArray(node.permissions, ['admin']) !== -1;
    });

    $osf.applyBindings({nodes: allNodes}, '#obGoToProject');
    $osf.applyBindings({nodes: registrationSelection, enableComponents: true}, '#obRegisterProject');
    $osf.applyBindings({nodes: uploadSelection}, '#obUploader');
    $osf.applyBindings({nodes: allNodes}, '#obCreateProject');
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
        var po = new ProjectOrganizer({
            placement : 'dashboard',
            divID: 'project-grid',
            filesData: data.data,
            multiselect : true
        });

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

// Initialize logfeed
new LogFeed('#logScope', '/api/v1/watched/logs/');
