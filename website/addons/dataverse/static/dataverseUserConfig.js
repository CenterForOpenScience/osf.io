/**
 * Module that controls the Dataverse user settings. Includes Knockout view-model
 * for syncing data.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'language', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        global.DataverseUserConfig  = factory(ko, jQuery);
        $script.done('dataverseUserConfig');
    } else {
        global.DataverseUserConfig  = factory(ko, jQuery);
    }
}(this, function(ko, $) {

    ko.punches.enableAll();
    var language = $.osf.Language.Addons.dataverse;

    function ViewModel(url) {
        var self = this;
        self.userHasAuth = ko.observable(false);
        self.dataverseUsername = ko.observable();
        self.dataversePassword = ko.observable();
        self.connected = ko.observable();
        self.urls = ko.observable({});
        // Whether the initial data has been loaded
        self.loaded = ko.observable(false);

        self.showDeleteAuth = ko.computed(function() {
            return self.loaded() && self.userHasAuth();
        });
        self.showInputCredentials = ko.computed(function() {
            return self.loaded() && (!self.userHasAuth() || !self.connected());
        });
        self.credentialsChanged = ko.computed(function() {
           return self.userHasAuth() && !self.connected();
        });

        // Update above observables with data from the server
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            success: function(response) {
                var data = response.result;
                self.userHasAuth(data.userHasAuth);
                self.urls(data.urls);
                self.loaded(true);
                self.dataverseUsername(data.dataverseUsername);
                self.connected(data.connected)
            },
            error: function(xhr, textStatus, error){
                console.error(textStatus); console.error(error);
                self.changeMessage(language.userSettingsError, 'text-warning');
            }
        })

        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info')

        /** Send POST request to authorize Dataverse */
        self.sendAuth = function() {
            return $.ajax({
                url: self.urls().create,
                data: ko.toJSON({
                    dataverse_username: self.dataverseUsername,
                    dataverse_password: self.dataversePassword
                }),
                contentType: 'application/json',
                type: 'POST',
                success: function() {
                    // User now has auth
                    self.userHasAuth(true);
                    self.connected(true);
                    self.changeMessage(language.authSuccess, 'text-info', 5000);
                },
                error: function(xhr, textStatus, error) {
                    var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
                    self.changeMessage(errorMessage, 'text-danger');
                }
            });
        }

       /** Pop up confirm dialog for deleting user's credentials. */
        self.deleteKey = function() {
            bootbox.confirm({
                title: 'Delete Dataverse Token?',
                message: language.confirmUserDeauth,
                callback: function(confirmed) {
                    if (confirmed) {
                        sendDeauth();
                    }
                }
            });
        };

       /** Send DELETE request to deauthorize Dataverse */
        function sendDeauth() {
            return $.ajax({
                url: self.urls().delete,
                type: 'DELETE',
                success: function() {
                    // Page must be refreshed to remove the list of authorized nodes
                    location.reload()

                    // KO logic. Uncomment if page ever doesn't need refreshing
                    // self.userHasAuth(false);
                    // self.connected(false);
                    // self.dataverseUsername('');
                    // self.dataversePassword('');
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

    };

    function DataverseUserConfig(selector, url) {
        // Initialization code
        var self = this;
        self.selector = selector;
        self.url = url;
        // On success, instantiate and bind the ViewModel
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, '#dataverseAddonScope');
    }
    return DataverseUserConfig;
}));