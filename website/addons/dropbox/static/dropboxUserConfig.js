/**
* View model that controls the Dropbox configuration on the user settings page.
*/
'use strict';
var ko = require('knockout');
require('knockout-punches');
ko.punches.enableAll();
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var language = require('osfLanguage').Addons.dropbox;
var osfHelpers = require('osfHelpers');
function ViewModel(url) {
    var self = this;
    self.userHasAuth = ko.observable(false);
    // Whether the auth token is valid
    self.validCredentials = ko.observable(true);
    self.dropboxName = ko.observable();
    self.urls = ko.observable({});
    // Whether the initial data has been loaded.
    self.loaded = ko.observable(false);
    self.nNodesAuthorized = 0;
    // Update above observables with data from server
    $.ajax({
        url: url, type: 'GET', dataType: 'json',
        success: function(response) {
            var data = response.result;
            self.userHasAuth(data.userHasAuth);
            self.dropboxName(data.dropboxName);
            self.urls(data.urls);
            self.loaded(true);
            self.validCredentials(data.validCredentials);
            self.nNodesAuthorized = data.nNodesAuthorized;
            if (!self.validCredentials()) {
                self.changeMessage('Could not retrieve Dropbox settings at ' +
                    'this time. The Dropbox addon credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing Dropbox.',
                    'text-warning');
            } else if (self.userHasAuth() && self.nNodesAuthorized === 0) {
                self.changeMessage('Add-on successfully authorized. To link this add-on to an OSF project, ' +
                    'go to the settings page of the project, enable Dropbox, and choose content to connect.',
                    'text-success');
            }
        },
        error: function(xhr, textStatus, error){
            self.changeMessage('Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.', 'text-warning');
            Raven.captureMessage('Could not GET Dropbox settings', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        }
    });
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    /** Send DELETE request to deauthorize Dropbox */
    function sendDeauth() {
        return $.ajax({
            url: self.urls().delete,
            type: 'DELETE',
            success: function() {
                // Page must be refreshed to remove the list of authorized nodes
                window.location.reload();
            },
            error: function(textStatus, error) {
                self.changeMessage(language.deauthError, 'text-danger');
                Raven.captureMessage('Could not deauthorize Dropbox.', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            }
        });
    }

    /** Change the flashed status message */
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

    /** Pop up confirm dialog for deleting user's access token. */
    self.deleteKey = function() {
        bootbox.confirm({
            title: 'Delete Dropbox Token?',
            message: language.confirmDeauth,
            callback: function(confirmed) {
                if (confirmed) {
                    sendDeauth();
                }
            }
        });
    };
}

function DropboxUserConfig(selector, url) {
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, selector);
}
module.exports = DropboxUserConfig;
