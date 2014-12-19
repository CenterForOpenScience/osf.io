/**
* View model that controls the Github configuration on the user settings page.
*/
'use strict';
var ko = require('knockout');
require('knockout-punches');
ko.punches.enableAll();
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var language = require('osfLanguage').Addons.github;
var osfHelpers = require('osfHelpers');

    function ViewModel(url) {
        self.userHasAuth = ko.observable(false);
        self.urls = ko.observable({});
        // Whether the initial data has been loaded.
        self.loaded = ko.observable(false);
        // Update above observables with data from server
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.result;
                self.userHasAuth(data.userHasAuth);
                self.urls(data.urls);
                self.loaded(true);
            },
            error: function(xhr, textStatus, error){
                self.changeMessage('Could not retrieve settings. Please refresh the page or ' +
                    'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                    'problem persists.', 'text-warning');
                Raven.captureMessage('Could not GET Github settings', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            }
        });

        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');


        /** Send DELETE request to deauthorize Github */
        function sendDeauth() {
            return $.ajax({
                url: self.urls().delete,
                type: 'DELETE',
                success: function() {

                     // Page must be refreshed to remove the list of authorized nodes
                    location.reload()
                },
                error: function() {
                    self.changeMessage(language.deauthError, 'text-danger');
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
                title: 'Delete Github Token?',
                message: language.confirmDeauth,
                callback: function(confirmed) {
                    if (confirmed) {
                        sendDeauth();
                    }
                }
            });
        };
    }

    function GithubUserConfig(selector, url) {
        var self = this;
        self.selector = selector;
        self.url = url;
        // On success, instantiate and bind the ViewModel
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, '#githubAddonScope');
    }

    module.exports = GithubUserConfig;