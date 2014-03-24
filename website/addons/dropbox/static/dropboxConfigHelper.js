this.DropboxConfigManager = (function(ko, $, bootbox) {
    'use strict';

    var ViewModel = function(data) {
        var self = this;
        self.ownerName = data.ownerName;
        self.nodeHasAuth = data.nodeHasAuth;
        self.userHasAuth = data.userHasAuth;
        self.selected = ko.observable(data.folder);
        self.folders = ko.observableArray(data.folders);
        self.urls = data.urls;
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        function onSubmitSuccess(response) {
            self.message(response.message);
            self.messageClass('text-success');
            setTimeout(function() {
                self.message('');
            }, 2000);
        }

        function onSubmitError(xhr, textStatus, error) {
            self.message('Could not change settings. Please try again later.');
            self.messageClass('text-danger');
        }

        self.submitSettings = function() {
            $.osf.putJSON(self.urls.config, ko.toJS(self),
                onSubmitSuccess, onSubmitError);
        };

        /**
         * Send DELETE request to deauthorize this node.
         */
        function sendDeauth() {
            return $.ajax({
                url: self.urls.deauthorize,
                type: 'DELETE',
                success: function() {
                    window.location.reload();
                },
                error: function(xhr, textStatus, error) {
                    self.message('Could not deauthorize because of an error. Please try again later.');
                    self.messageClass('text-danger');
                }
            });
        }

        self.deauthorize = function() {
            bootbox.confirm({
                title: 'Deauthorize Dropbox?',
                message: 'Are you sure you want to remove this Dropbox authorization?',
                callback: function(confirmed) {
                    if (confirmed) {
                        sendDeauth();
                    }
                }
            });
        };

        /**
         * Send PUT request to import access token from user profile.
         */
        self.importAuth = function() {
            return $.osf.putJSON(self.urls.importAuth, {},
                function() {
                    window.location.reload();
                });
        };

    };

    // Public API
    function DropboxConfigManager(selector, url) {
        var self = this;
        self.url = url;
        self.selector = selector;
        self.$elem = $(selector);
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                var viewModel = new ViewModel(response.result);
                ko.applyBindings(viewModel, self.$elem[0]);
            },
            error: function(xhr, error, textError) {
                // TODO(sloria)
                console.log('an error occurred getting dropbox info');
            }
        });
    }

    return DropboxConfigManager;

})(ko, jQuery, bootbox);
