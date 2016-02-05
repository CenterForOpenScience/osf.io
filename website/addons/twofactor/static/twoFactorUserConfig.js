'use strict';

require('./user-cfg.css');

var ko = require('knockout');
var Raven = require('raven-js');
var $ = require('jquery');
var bootbox = require('bootbox');
require('jquery-qrcode');

var osfHelpers = require('js/osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');


function ViewModel(settingsUrl, qrCodeSelector) {
    var self = this;
    ChangeMessageMixin.call(self);

    self.settingsUrl = settingsUrl;
    self.qrCodeSelector = qrCodeSelector;
    self.tfaCode = ko.observable('');

    self.isEnabled = ko.observable(false);
    self.isConfirmed = ko.observable(false);
    self.secret = ko.observable('');

    self.urls = {};
}
$.extend(ViewModel.prototype, ChangeMessageMixin.prototype);


ViewModel.prototype.initialize = function() {
    var self = this;
    return self.fetchFromServer().then(self.updateFromData.bind(self));
};

ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    self.isEnabled(data.is_enabled);
    self.isConfirmed(data.is_confirmed);
    self.secret(data.secret);
    self.urls = data.urls;
    if (self.isEnabled()) {
        // Initialize QR Code
        if (!self.urls.otpauth) {
            throw new Error('Tried to initialize jQuery.fn.qrcode without a otpauth URL');
        } else {
            $(self.qrCodeSelector).qrcode(self.urls.otpauth);
        }
    }
};

ViewModel.prototype.fetchFromServer = function() {
    var self = this;
    return $.getJSON(self.settingsUrl)
        .then(function(response) {
            return response.result;
        })
        .fail(function(xhr, status, error) {
            Raven.captureMessage('Failed to fetch two-factor settings.', {
                xhr: xhr,
                status: status,
                error: error
            });
            self.changeMessage('Could not retrieve two-factor settings at ' +
                'this time. Please refresh the page. ' +
                'If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.', 'text-danger', 5000);
        });
};

ViewModel.prototype.submitSettings = function() {
    var self = this;
    return osfHelpers.putJSON(
        self.settingsUrl, {
            code: self.tfaCode()
        }
    ).done(function() {
        self.isConfirmed(true);
        $('#TfaVerify').slideUp();
    }).fail(function(xhr, status, error) {
        Raven.captureMessage('Failed to update two-factor settings.', {
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
    return $.ajax({
            method: 'DELETE',
            url: self.urls.disable,
            dataType: 'json'
        })
        .done(function(response) {
            self.isEnabled(false);
            self.isConfirmed(false);
            $(self.qrCodeSelector).html('');
        })
        .fail(function(xhr, status, error) {
            Raven.captureMessage('Failed to disable two-factor.', {
                xhr: xhr,
                status: status,
                error: error
            });
            self.changeMessage(
                'Could not disable two-factor authentication at this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.',
                5000);
        });
};

ViewModel.prototype.disableTwofactor = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disable Two-factor Authentication',
        message: 'Are you sure you want to disable two-factor authentication?',
        callback: function(confirmed) {
            if (confirmed) {
                self.disableTwofactorConfirm.call(self);
            }
        },
        buttons:{
            confirm:{
                label:'Disable',
                className:'btn-danger'
            }
        }
    });
};

ViewModel.prototype.enableTwofactorConfirm = function() {
    var self = this;
    return osfHelpers.postJSON(self.urls.enable, {})
        .done(function(response) {
            self.updateFromData(response.result);
        })
        .fail(function(xhr, status, error) {
            Raven.captureMessage('Failed to enable two-factor.', {
                xhr: xhr,
                status: status,
                error: error
            });
            self.changeMessage(
                'Could not enable two-factor authentication at this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.',
                5000);
        });
};

ViewModel.prototype.enableTwofactor = function() {
    var self = this;
    bootbox.confirm({
        title: 'Enable Two-factor Authentication',
        message: 'Enabling two-factor authentication will not immediately activate ' +
            'this feature for your account. You will need to follow the ' +
            'steps that appear below to complete the activation of two-factor authentication ' +
            'for your account.',
        callback: function(confirmed) {
            if (confirmed) {
                self.enableTwofactorConfirm.call(self);
            }
        },
        buttons:{
            confirm:{
                label:'Enable',
            }
        }
    });
};

// Public API
function TwoFactorUserConfig(settingsUrl, scopeSelector, qrCodeSelector) {
    var self = this;
    self.viewModel = new ViewModel(settingsUrl, qrCodeSelector);
    self.viewModel.initialize();
    osfHelpers.applyBindings(self.viewModel, scopeSelector);
}
module.exports = {
    TwoFactorUserConfig: TwoFactorUserConfig,
    _ViewModel: ViewModel
};
