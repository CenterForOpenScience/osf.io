'use strict';

require('./user-cfg.css');

var ko = require('knockout');
var Raven = require('raven-js');
var $ = require('jquery');
var bootbox = require('bootbox');
require('jquery-qrcode');

var osfHelpers = require('js/osfHelpers');

var SETTINGS_URL = '/api/v1/settings/twofactor/';

function ViewModel(qrCodeSelector) {
    var self = this;
    self.qrCodeSelector = qrCodeSelector;
    self.tfaCode = ko.observable('');

    self.message = ko.observable('');
    self.messageClass = ko.observable('');

    self.isEnabled = ko.observable(false);
    self.isConfirmed = ko.observable(false);
    self.secret = ko.observable('');

    self.urls = {};
};

ViewModel.prototype.initialize = function() {
    var self = this;
    self.fetchFromServer().then(self.updateFromData);
};

ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    self.isEnabled(data.is_enabled);
    self.isConfirmed(data.is_confirmed);
    self.secret(data.secret);
    self.urls = data.urls;
    if (self.isEnabled()) {
        // Initialize QR Code
        $(self.qrCodeSelector).qrcode(self.urls.otpauth);
    }
};

ViewModel.prototype.fetchFromServer = function() {
    var self = this;
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
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
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

ViewModel.prototype.submitSettings = function() {
    var self = this;
    osfHelpers.putJSON(
        SETTINGS_URL, {
            code: self.tfaCode()
        }
    ).done(function() {
        self.isConfirmed(true);
        $('#TfaVerify').slideUp();
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

ViewModel.prototype.disableTwofactorConfirm = function() {
    var self = this;
    $.ajax({
            method: 'DELETE',
            url: self.urls.disable,
            dataType: 'json'
        })
        .done(function(response) {
            self.isEnabled(false);
            self.isConfirmed(false);
            $(self.qrCodeSelector).html('');
            self.changeMessage(
                'Successfully disabled Two-factor Authentication.',
                'text-success',
                5000);
        })
        .fail(function(xhr, status, error) {
            Raven.captureMessage('Failed to disable twofactor.', {
                xhr: xhr,
                status: status,
                error: error
            });
            self.changeMessage(
                'Could not disable Two-factor Authentication at this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.',
                5000);
        });
};

ViewModel.prototype.disableTwofactor = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disable Two-factor Authentication',
        message: 'Are you sure you want to disable Two-factor Authentication?',
        callback: function(confirmed) {
            if (confirmed) {
                self.disableTwofactorConfirm.call(self);
            }
        }
    });
};

ViewModel.prototype.enableTwofactorConfirm = function() {
    var self = this;
    osfHelpers.postJSON(self.urls.enable, {})
        .done(function(response) {
            self.changeMessage(
                'Successfully enabled Two-factor Authentication.',
                'text-success',
                5000);
            self.updateFromData(response.result);
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

ViewModel.prototype.enableTwofactor = function() {
    var self = this;
    bootbox.confirm({
        title: 'Enable Two-factor Authentication',
        message: 'Enabling Two-factor Authentication will not immediately activate this feature for your account. You will need to follow the steps that appear below to activate Two-factor Authentication for your account.',
        callback: function(confirmed) {
            if (confirmed) {
                self.enableTwofactorConfirm.call(self);
            }
        }
    });
};

// Public API
function TwoFactorUserConfig(scopeSelector, qrCodeSelector) {
    var self = this;
    self.viewModel = new ViewModel(qrCodeSelector);
    self.viewModel.initialize();
    osfHelpers.applyBindings(self.viewModel, scopeSelector);
}
module.exports = TwoFactorUserConfig;
