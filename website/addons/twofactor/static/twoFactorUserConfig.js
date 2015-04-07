'use strict';

require('./user-cfg.css');

var ko = require('knockout');
var Raven = require('raven-js');
var $ = require('jquery');
require('jquery-qrcode');

var osfHelpers = require('js/osfHelpers');

var SETTINGS_URL = '/api/v1/settings/twofactor/';
var ENABLE_URL = '/api/v1/settings/twofactor/enable/';

function ViewModel(qrCodeSelector, otpURL) {
    var self = this;
    self.qrCodeSelector = qrCodeSelector;
    self.tfaCode = ko.observable('');

    self.message = ko.observable('');
    self.messageClass = ko.observable('');

    self.isEnabled = ko.observable(false);
    self.isConfirmed = ko.observable(false);
    self.secret = ko.observable('');

    self.showCode = ko.pureComputed(function() {
        return self.isEnabled() && self.isConfirmed();
    });

    self.initialize = function() {
        self.fetchFromServer().then(self.updateFromData);
    };

    self.updateFromData = function(data) {
        self.isEnabled(data.is_enabled);
        self.isConfirmed(data.is_confirmed);
        self.secret(data.secret);
        if(self.isEnabled()) {
            // Initialize QR Code
            $(self.qrCodeSelector).qrcode(otpURL);
        }
    };

    self.fetchFromServer = function() {
        return $.getJSON(SETTINGS_URL)
            .then(function(response) {
                return response.result;
            })
            .fail(function(xhr, status, error) {
                Raven.captureMessage('Failed to fetch twofactor settings.', {
                    xhr: xhr,
                    status: status,
                    error: error
                });
                self.changeMessage('Could not retrieve Two-factor settings at ' +
                                   'this time. Please refresh the page. ' +
                                   'If the problem persists, email ' +
                                   '<a href="mailto:support@osf.io">support@osf.io</a>.', 'text-danger', 5000);                
            });
    };

    /** Change the flashed message. */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            window.setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    self.submitSettings = function() {
        osfHelpers.putJSON(
            SETTINGS_URL,
            {code: self.tfaCode()}
        ).done(function() {
            $('#TfaVerify').slideUp(function() {
                $('#TfaDeactivate').slideDown();
            });
        }).fail(function(xhr, status, error) {
            Raven.captureMessage('Failed to update twofactor settings.', {
                xhr: xhr,
                status: status,
                error: error
            });

            if (xhr.status === 403) {
                self.changeMessage('Verification failed. Please enter your verification code again.',
                                    'text-danger', 5000);
            } else {
                self.changeMessage(
                    'Unexpected HTTP Error (' + xhr.status + '/' + xhr.statusText + ')',
                    'text-danger',
                    5000);
            }
        });
    };

    self.enableTwofactor = function() {
        osfHelpers.postJSON(ENABLE_URL, {})
            .done(function(response) {
                self.changeMessage(
                    'Successfully enabled Two-factor Authentication.',
                    'text-success',
                    5000);
            })
            .fail(function(xhr, status, error) {
                Raven.captureMessage('Failed to enable twofactor.', {
                    xhr: xhr,
                    status: status,
                    error: error
                });                
                self.changeMessage(
                    'Could not enable Two-factor Authentication at this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:support@osf.io">support@osf.io</a>.',
                    5000);
            });
    };
}

// Public API
function TwoFactorUserConfig(scopeSelector, qrCodeSelector, otpURL) {
    var self = this;
    self.viewModel = new ViewModel(qrCodeSelector, otpURL);
    self.viewModel.initialize();
    osfHelpers.applyBindings(self.viewModel, scopeSelector);
}
module.exports = TwoFactorUserConfig;
