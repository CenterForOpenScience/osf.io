/**
 * JS module included on every page of the OSF. Site-wide initialization
 * code goes here.
 */
'use strict';
// CSS used on every page
require('../../vendor/bootstrap-editable-custom/css/bootstrap-editable.css');
require('../../vendor/bower_components/jquery-ui/themes/base/minified/jquery.ui.resizable.min.css');
require('../../css/bootstrap-xl.css');
require('../../css/animate.css');
require('../../css/search-bar.css');
require('font-awesome-webpack');

var $ = require('jquery');
require('jquery.cookie');

require('js/crossOrigin.js');
var $osf = require('js/osfHelpers');
var NavbarControl = require('js/navbarControl');
var Raven = require('raven-js');
var moment = require('moment');
var KeenTracker = require('js/keen');
var DevModeControls = require('js/devModeControls');
var bootbox = require('bootbox');

// Prevent IE from caching responses
$.ajaxSetup({cache: false});

// Polyfill for String.prototype.endsWith
if (String.prototype.endsWith === undefined) {
    String.prototype.endsWith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    };
}

// Apply an empty view-model to the navbar, just so the tooltip bindingHandler
// can be used
// $osf.applyBindings({}, '#navbarScope');

$('[rel="tooltip"]').tooltip();

// If there isn't a user logged in, show the footer slide-in
var sliderSelector = '#footerSlideIn';
var SlideInViewModel = function (){
    var self = this;
    self.elem = $(sliderSelector);

    var dismissed = false;

    try {
        dismissed = dismissed || window.localStorage.getItem('slide') === '0';
    } catch (e) {}

    dismissed = dismissed || $.cookie('slide') === '0';

    if (this.elem.length > 0 && !dismissed) {
        setTimeout(function () {
            self.elem.slideDown(1000);
        }, 3000);
    }
    self.dismiss = function() {
        self.elem.slideUp(1000);
        try {
            window.localStorage.setItem('slide', '0');
        } catch (e) {
            $.cookie('slide', '0', { expires: 1, path: '/'});
        }
        self.trackClick('Dismiss');
    };
    // Google Analytics click event tracking
    self.trackClick = function(source) {
        window.ga('send', 'event', 'button', 'click', source);
        //in order to make the href redirect work under knockout onclick binding
        return true;
    };
};


$(document).on('click', '.panel-heading', function(){
    var toggle = $(this).find('.project-toggle');
    if(toggle.length > 0){
        var widget = $(this).closest('.panel');
        var up = toggle.find('.fa.fa-angle-up');
        var down = toggle.find('.fa.fa-angle-down');
        if(up.length > 0) {
            up.removeClass('fa fa-angle-up').addClass('fa fa-angle-down');
        }
        if(down.length > 0) {
            down.removeClass('fa fa-angle-down').addClass('fa fa-angle-up');
        }

        widget.find('.panel-body').slideToggle();
    }
});

//choose which emails/users to add to an account and which to deny
function confirmEmails(emailsToAdd) {
    if (emailsToAdd.length > 0) {
        var confirmedEmailURL = window.contextVars.confirmedEmailURL;
        var email = emailsToAdd.splice(0, 1)[0];
        var title;
        var requestMessage;
        var confirmMessage;
        var nopeMessage;
        if (email.user_merge) {
            title = 'Merge account';
            requestMessage = 'Would you like to merge \<b>' + email.address + '\</b> into your account?  ' +
                'This action is irreversable.';
            confirmMessage = '\<b>' + email.address + '\</b> has been merged into your account.';
            nopeMessage = 'You have chosen to not merge \<b>' + email.address + '\</b>  into your account. ' +
                'If you change your mind, visit the \<a href="/settings/account/">user settings page</a>.';
        }
        else {
            title = 'Add email';
            requestMessage = 'Would you like to add \<b>' + email.address + '\</b> to your account?';
            confirmMessage = '\<b>' + email.address + '\</b> has been added into your account.';
            nopeMessage = 'You have chosen not to add \<b>' + email.address + '\</b> to your account.' +
                'If you change your mind, visit the \<a href="/settings/account/">user settings page</a>.';
        }

        var confirmFailMessage = 'There are a problem adding \<b>' + email.address +
            '\</b>. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.';

        var cancelFailMessage = 'There are a problem removing \<b>' + email.address +
            '\</b>. Please contact <a href="mailto: support@osf.io">support@osf.io</a> if the problem persists.';

        bootbox.dialog({
            title: title,
            message: requestMessage,
            onEscape: function () {
            },
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
                            confirmEmails(emailsToAdd);
                        }).fail(function (xhr, textStatus, error) {
                            Raven.captureMessage('Could not add email', {
                                url: confirmedEmailURL,
                                textStatus: textStatus,
                                error: error
                            });
                            $osf.growl('Error',
                                confirmFailMessage,
                                'danger'
                            );
                        });
                        confirmEmails(emailsToAdd);
                    }
                },
                cancel: {
                    label: 'Do not add email',
                    className: 'btn-default',
                    callback: function () {
                        $.ajax({
                            type: 'delete',
                            url: confirmedEmailURL,
                            contentType: 'application/json',
                            dataType: 'json',
                            data: JSON.stringify(email)
                        }).done(function () {
                            $osf.growl('Warning', nopeMessage, 'warning', 8000);
                            confirmEmails(emailsToAdd);
                        }).fail(function (xhr, textStatus, error) {
                            Raven.captureMessage('Could not remove email', {
                                url: confirmedEmailURL,
                                textStatus: textStatus,
                                error: error
                            });
                            $osf.growl('Error',
                                cancelFailMessage,
                                'danger'
                            );
                        });
                    }
                }
            }
        });

    }
}


$(function() {
    if(/MSIE 9.0/.test(window.navigator.userAgent) ||
       /MSIE 8.0/.test(window.navigator.userAgent) ||
       /MSIE 7.0/.test(window.navigator.userAgent) ||
       /MSIE 6.0/.test(window.navigator.userAgent)) {
        $('.placeholder-replace').show();
    }
    if (
        $(sliderSelector).length > 0 &&
        window.contextVars.node
    ) {
        $osf.applyBindings(new SlideInViewModel(), sliderSelector);
    }

    var affix = $('.osf-affix');
    if(affix.length){
        $osf.initializeResponsiveAffix();
    }
    new NavbarControl('.osf-nav-wrapper');
    new DevModeControls('#devModeControls', '/static/built/git_logs.json');
    if(window.contextVars.keenProjectId){
        var params = {};
        params.currentUser = window.contextVars.currentUser;
        params.node = window.contextVars.node;

        //Don't track PhantomJS visits with KeenIO
        if(!(/PhantomJS/.test(navigator.userAgent))){
            new KeenTracker(window.contextVars.keenProjectId, window.contextVars.keenWriteKey, params);
        }
    }

    confirmEmails(window.contextVars.currentUser.emailsToAdd);

});
