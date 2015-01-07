var ko = require('knockout');
var $ = require('jquery');
require('./jquery.qrcode.min.js');

var osfHelpers = require('osfHelpers');

var SETTINGS_URL = '/api/v1/settings/twofactor/';

function ViewModel(qrCodeSelector, otpURL) {
    var self = this;
    self.qrCodeSelector = qrCodeSelector;
    self.tfaCode = ko.observable('');

    self.message = ko.observable('');
    self.messageClass = ko.observable('');
    // Initialize QR Code
    $(self.qrCodeSelector).qrcode(otpURL);

    /** Change the flashed message. */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    self.submitSettings = function() {
        osfHelpers.postJSON(
            SETTINGS_URL,
            {code: self.tfaCode()}
        ).done(function() {
            $('#TfaVerify').slideUp(function() {
                $('#TfaDeactivate').slideDown();
            });
        }).fail(function(e) {
            if (e.status === 403) {
                self.changeMessage('Verification failed. Please enter your verification code again.',
                                    'text-danger', 5000);
            } else {
                self.changeMessage(
                    'Unexpected HTTP Error (' + e.status + '/' + e.statusText + ')',
                    'text-danger',
                    5000);
            }
        });
    };
}

// Public API
function TwoFactorUserConfig(scopeSelector, qrCodeSelector, otpURL) {
    var self = this;
    self.viewModel = new ViewModel(qrCodeSelector, otpURL);
    osfHelpers.applyBindings(self.viewModel, scopeSelector);
}
module.exports = TwoFactorUserConfig;
