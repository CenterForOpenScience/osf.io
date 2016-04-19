/**
 * Initialization code for the dashboard pages.
 */

'use strict';

var Raven = require('raven-js');
var $ = require('jquery');
var jstz = require('jstimezonedetect');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var MyProjects = require('js/myProjects.js').MyProjects;
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
require('loaders.css/loaders.min.css');

var confirmedEmailURL = window.contextVars.confirmedEmailURL;
var removeConfirmedEmailURL = window.contextVars.removeConfirmedEmailURL;


//choose which emails/users to add to an account and which to deny
function confirm_emails(emails) {
    if (emails.length > 0) {
        var email = emails.splice(0,1)[0];
        var title;
        var requestMessage;
        var confirmMessage;
        var nopeMessage;
        if (email.user_merge) {
            title =  'Merge account';
            requestMessage = 'Would you like to merge \<b>' + email.address + '\</b> into your account?  ' +
                'This action is irreversable.';
            confirmMessage = '\<b>' + email.address + '\</b> has been merged into your account.';
            nopeMessage =  'You have chosen to not merge \<b>'+ email.address + '\</b>  into your account. ' +
                'If you change your mind, visit the \<a href="/settings/account/">user settings page</a>.';
        }
        else {
            title = 'Add email';
            requestMessage = 'Would you like to add \<b>' + email.address + '\</b> to your account?';
            confirmMessage = '\<b>' + email.address + '\</b> has been added into your account.';
            nopeMessage = 'You have chosen not to add \<b>' + email.address + '\</b> to your account.' +
             'If you change your mind, visit the \<a href="/settings/account/">user settings page</a>.';
        }

        var failSuccessMessage = 'There are a problem adding \<b>' + email.address +
            '\</b>. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.';

        var failCancelMessage = 'There are a problem removing \<b>' + email.address +
            '\</b>. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.';

        bootbox.dialog({
            title: title,
            message: requestMessage,
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
                            email
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
                            email
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
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    }
};

$(document).ready(function() {
    m.mount(document.getElementById('dashboard'), m.component(MyProjects, {wrapperSelector : '#dashboard'}));
    // TODO: new data does not have timezone information
    //ensureUserTimezone(result.timezone, result.locale, result.id);

    // Appears in 10 second if the spinner is still there.
    setTimeout(function(){
        if($('#dashboard>.ball-scale').length > 0) {
            $('#dashboard').append('<div class="text-danger text-center text-bigger">This is taking longer than normal. <br>  Try reloading the page. If the problem persist contact us at support@cos.io.</div>');
        }
    }, 10000);

    // Add active class to navigation for my projects page
    $('#osfNavMyProjects').addClass('active');
});

