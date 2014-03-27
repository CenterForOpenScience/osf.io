/**
 * View model that controls the Dropbox configuration on the user settings page.
 */
(function($, global, undefined) {
    'use strict';

    var language = $.osf.Language.Addons.dropbox;

    function ViewModel(data) {
        self.userHasAuth = ko.observable(data.userHasAuth);
        self.urls = data.urls;
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        /** Whether to show the Delete Access Token Button */
        self.showDelete = ko.computed(function() {
            // Only show if user already authorized Dropbox
            return self.userHasAuth();
        });

        /** Whether to show the Create Access Token Button */
        self.showCreate = ko.computed(function() {
            // Only show if user has NOT authorized Dropbox
            return !self.userHasAuth();
        });

        /** Send DELETE request to deauthorize Dropbox */
        function sendDeauth() {
            return $.ajax({
                url: self.urls.delete,
                type: 'DELETE',
                success: function() {
                    // User no longer has auth; update viewmodel
                    self.userHasAuth(false);
                    self.changeMessage(language.deauthSuccess, 'text-info', 5000);
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
        console.log('instantiation');
        self.selector = selector;
        self.url = url;
        $.ajax({
            url: self.url, type: 'GET', dataType: 'json'
        })
        .done(function(response) {
            console.log(response);
            console.log('Binding VM');
            // On success, instantiate and bind the ViewModel
            self.viewModel = new ViewModel(response.result);
            $.osf.applyBindings(self.viewModel, '#dropboxAddonScope');
        });
    }

    // Export
    global.DropboxUserConfig = DropboxUserConfig;
    $script.done('dropboxUserConfig');

})(jQuery, window);
