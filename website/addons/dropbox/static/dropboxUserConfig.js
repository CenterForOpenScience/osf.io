/**
 * View model that controls the Dropbox configuration on the user settings page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'language'], factory);
    } else if (typeof $script === 'function') {
        global.DropboxUserConfig  = factory(ko, jQuery);
        $script.done('dropboxUserConfig');
    } else {
        global.DropboxUserConfig  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    var language = $.osf.Language.Addons.dropbox;

    function ViewModel(url) {
        self.userHasAuth = ko.observable(false);
        self.dropboxName = ko.observable();
        self.urls = ko.observable({});
        // Whether the initial data has been loaded.
        self.loaded = ko.observable(false);
        // Update above observables with data from server
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.result;
                self.userHasAuth(data.userHasAuth);
                self.dropboxName(data.dropboxName);
                self.urls(data.urls);
                self.loaded(true);
            },
            error: function(xhr, textStatus, error){
                console.error(textStatus); console.error(error);
                self.changeMessage('Could not retrieve settings. Please refresh the page or ' +
                    'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
                    'problem persists.', 'text-warning');
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
                    location.reload()

                    // KO logic. Uncomment if page ever doesn't need refreshing
                    // self.userHasAuth(false);
                    // self.changeMessage(language.deauthSuccess, 'text-info', 5000);

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
        $.osf.applyBindings(self.viewModel, '#dropboxAddonScope');
    }
    return DropboxUserConfig;
}));
