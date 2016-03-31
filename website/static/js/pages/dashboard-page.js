/**
 * Initialization code for the dashboard pages. Starts up the Project Organizer
 * and binds the onboarder Knockout components.
 */

'use strict';

var Raven = require('raven-js');
var ko = require('knockout');
var $ = require('jquery');
var jstz = require('jstimezonedetect');
var bootbox = require('bootbox');

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

var confirmedEmailURL = window.contextVars.confirmedEmailURL;
var removeConfirmedEmailURL = window.contextVars.removeConfirmedEmailURL;


//choose which emails/users to add to an account and which to deny
function confirm_emails(emails) {
    if (emails.length > 0) {
        var email = emails.splice(0,1);
        var title;
        var mergeMessage;
        var confirmMessage;
        var nopeMessage;
        if (email[0].user_merge) {
            title =  'Merge account';
            mergeMessage = 'Would you like to merge \<b>' + email[0].address + '\</b> into your account?  ' +
                'This action is irreversable.';
            confirmMessage = '\<b>' + email[0].address + '\</b> has been merged into your account.';
            nopeMessage =  'You have chosen to not merge \<b>'+ email[0].address + '\</b>  into your account. ' +
                'If you change your mind, visit the \<a href="/settings/account/">user settings page</a>.';
        }
        else {
            title = 'Add email';
            mergeMessage = 'Would you like to add \<b>' + email[0].address + '\</b> to your account?';
            confirmMessage = '\<b>' + email[0].address + '\</b> has been added into your account.';
            nopeMessage = 'You have chosen not to add \<b>' + email[0].address + '\</b> to your account.' +
             'If you change your mind, visit the \<a href="/settings/account/">user settings page</a>.';
        }

        var failSuccessMessage = 'There are a problem adding \<b>' + email[0].address +
            '\</b>. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.';

        var failCancelMessage = 'There are a problem removing \<b>' + email[0].address +
            '\</b>. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.';

        bootbox.dialog({
            title: title,
            message: mergeMessage,
            onEscape: function() {},
            backdrop: true,
            closeButton: true,
            buttons: {
                confirm: {
                    label: 'Add email',
                    className: 'btn-success',
                    callback: function () {
                        $osf.putJSON(
                            confirmedEmailURL,
                            email[0]
                        ).done(function () {
                            $osf.growl('Success', confirmMessage, 'success', 3000);
                            confirm_emails(emails);
                        }).fail(function (xhr, textStatus, error) {
                            Raven.captureMessage('Could not add email', {
                                url: url,
                                textStatus: textStatus,
                                error: error
                            });
                            $osf.growl('Error',
                                failSuccessMessage,
                                'danger'
                            );
                        });
                        confirm_emails(emails);
                    }
                },
                cancel: {
                    label: 'Cancel',
                    className: 'btn-default',
                    callback: function () {
                        $osf.putJSON(
                            removeConfirmedEmailURL,
                            email[0]
                        ).done(function () {
                            $osf.growl('Warning', nopeMessage, 'warning', 8000);
                            confirm_emails(emails);
                        }).fail(function (xhr, textStatus, error) {
                            Raven.captureMessage('Could not remove email', {
                                url: url,
                                textStatus: textStatus,
                                error: error
                            });
                            $osf.growl('Error',
                                failCancelMessage,
                                'danger'
                            );
                        });
                    }
                }
            }
        });

    }
}

$.getJSON(confirmedEmailURL).done(function(response) {
        confirm_emails(response);
}).fail(function(xhr, textStatus, error) {
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
