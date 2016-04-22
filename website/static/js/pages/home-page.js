/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');
var bootbox = require('bootbox');


var QuickSearchProject = require('js/home-page/quickProjectSearchPlugin');
var NewAndNoteworthy = require('js/home-page/newAndNoteworthyPlugin');
var MeetingsAndConferences = require('js/home-page/meetingsAndConferencesPlugin');

var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';


var Raven = require('raven-js');
var jstz = require('jstimezonedetect');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
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
                                url: confirmedEmailURL,
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
                                url: confirmedEmailURL,
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

$(document).ready(function(){
    var osfHome = {
        view : function(ctrl, args) {
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('.row.m-t-lg', [
                            m(columnSizeClass, m.component(QuickSearchProject, {}))
                        ])
                    ]
                )),
                m('.newAndNoteworthy', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass, m('h3', 'Discover Public Projects'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(NewAndNoteworthy, {}))
                        ])

                    ]
                )),
                m('.meetings', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,  m.component(MeetingsAndConferences, {}))
                        ])

                    ]
                ))
            ];
        }
    };
    // If logged in...
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));
    $('#osfNavDashboard').addClass('active');

    $.getJSON(confirmedEmailURL).done(function(response) {
            confirm_emails(response);
    }).fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Could not fetch dashboard nodes.', {
            url: confirmedEmailURL, textStatus: textStatus, error: error
        });
    });


});
