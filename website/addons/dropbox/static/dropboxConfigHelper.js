this.DropboxConfigManager = (function(ko, $, bootbox) {
    'use strict';

    var ViewModel = function(data) {
        var self = this;

        self.updateFromData = function(data) {
            self.ownerName = data.ownerName;
            self.nodeHasAuth = ko.observable(data.nodeHasAuth);
            self.userHasAuth = ko.observable(data.userHasAuth);
            self.selected = ko.observable(data.folder);
            self.folders = ko.observableArray(data.folders);
            self.urls = data.urls;
        };

        self.updateFromData(data);
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        function onSubmitSuccess(response) {
            self.message('Successfully updated settings. Go to the <a href="' +
                self.urls.files + '">Files page</a> to view your files.');
            self.messageClass('text-success');
            setTimeout(function() {
                self.message('');
            }, 5000);
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
                        return sendDeauth();
                    }
                }
            });
        };

        function onImportSuccess(response) {
            // TODO(sloria): This doesn't work yet because the view doesn't update
            // so just reload for now.

            // var msg = response.message || 'Successfully imported access token from profile.';
            // // Update view model based on response
            // self.message(msg);
            // self.messageClass('text-success');
            // self.updateFromData(response.result);
            window.location.reload();
        }

        function onImportError() {
            self.message('Error occurred while importing access token.');
            self.messageClass('text-danger');
        }

        /**
         * Send PUT request to import access token from user profile.
         */
        self.importAuth = function() {
            return $.osf.putJSON(self.urls.importAuth, {}, onImportSuccess, onImportError);
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
