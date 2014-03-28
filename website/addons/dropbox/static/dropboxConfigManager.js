/**
 * Module that controls the Dropbox node settings. Includes Knockout view-model
 * for syncing data, and and HGrid for selecting a folder.
 */
// Load folderPicker dependency
$script.ready(['folderPicker'], function() {
    'use strict';

    /**
     * Knockout view model for the Dropbox node settings pane.
     */
    var ViewModel = function(data, folderPicker) {
        var self = this;

        // Auth information
        self.nodeHasAuth = ko.observable(data.nodeHasAuth);
        self.userHasAuth = ko.observable(data.userHasAuth);
        // Currently linked folder
        self.folder = ko.observable(data.folder);
        self.ownerName = ko.observable(data.ownerName);
        self.urls = data.urls;
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');
        // Whether or not folder picker is displayed
        self.showPicker = ko.observable(false);
        // CSS selector for the folder picker div
        self.folderPicker = folderPicker;
        // Currently selected folder
        self.selected = ko.observable();

        /**
         * Update the view model from data returned from the server.
         */
        self.updateFromData = function(data) {
            self.ownerName(data.ownerName);
            self.nodeHasAuth(data.nodeHasAuth);
            self.userHasAuth(data.userHasAuth);
            self.folder(data.folder);
        };

        /**
         * Whether or not to show the Import Access Token Button
         */
        self.showImport = ko.computed(function() {
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            return userHasAuth && !nodeHasAuth;
        });

        /** Whether or not to show the full settings pane. */
        self.showSettings = ko.computed(function() {
            return self.nodeHasAuth();
        });

        /** Whether or not to show the Create Access Token button */
        self.showTokenCreateButton = ko.computed(function() {
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            return !userHasAuth && !nodeHasAuth;
        });

        self.folderName = ko.computed(function() {
            if (self.nodeHasAuth() && self.folder()) {
                return self.folder().name;
            } else {
                return '';
            }
        });

        self.selectedFolderName = ko.computed(function() {
            if (self.userHasAuth() && self.selected()) {
                return self.selected().name;
            } else{
                return '';
            }
        });

        function onSubmitSuccess(response) {
            self.changeMessage('Successfully linked "' + self.selected().name +
                '". Go to the <a href="' +
                self.urls.files + '">Files page</a> to view your files.',
                'text-success', 5000);
            // Update folder in ViewModel
            self.folder(response.result.folder);
            self.selected(null);
        }

        function onSubmitError() {
            self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
        }

        /**
         * Send a PUT request to change the linked Dropbox folder.
         */
        self.submitSettings = function() {
            $.osf.putJSON(self.urls.config, ko.toJS(self),
                onSubmitSuccess, onSubmitError);
        };

        self.cancelSelection = function() {
            self.selected(null);
        };

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

        /**
         * Send DELETE request to deauthorize this node.
         */
        function sendDeauth() {
            return $.ajax({
                url: self.urls.deauthorize,
                type: 'DELETE',
                success: function() {
                    self.nodeHasAuth(false);
                    self.selected(null);
                    self.changeMessage('Deauthorized Dropbox.', 'text-warning', 3000);
                },
                error: function() {
                    self.changeMessage('Could not deauthorize because of an error. Please try again later.',
                        'text-danger');
                }
            });
        }

        /** Pop up a confirmation to deauthorize Dropbox from this node.
         *  Send DELETE request if confirmed.
         */
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
            var msg = response.message || 'Successfully imported access token from profile.';
            // Update view model based on response
            self.changeMessage(msg, 'text-success', 3000);
            self.updateFromData(response.result);
        }

        function onImportError() {
            self.message('Error occurred while importing access token.');
            self.messageClass('text-danger');
        }

        /**
         * Send PUT request to import access token from user profile.
         */
        self.importAuth = function() {
            bootbox.confirm({
                title: 'Import Dropbox Access Token?',
                message: 'Are you sure you want to authorize this project with your Dropbox access token?',
                callback: function(confirmed) {
                    if (confirmed) {
                        return $.osf.putJSON(self.urls.importAuth, {},
                            onImportSuccess, onImportError);
                    }
                }
            });
        };

        /** Callback for chooseFolder action.
        *   Just changes the ViewModel's self.selected observable to the selected
        *   folder.
        */
        function onPickFolder(evt, row) {
            evt.preventDefault();
            self.selected({name: 'Dropbox' + row.path, path: row.path});
            return false; // Prevent event propagation
        }

        // Hide +/- icon for root folder
        FolderPicker.Col.Name.showExpander = function(item) {
            return item.path !== '/';
        };

        /**
         * Activates the HGrid folder picker.
         */
        self.activatePicker = function() {
            $(self.folderPicker).folderpicker({
                onPickFolder: onPickFolder,
                // Fetch Dropbox folders with AJAX
                data: self.urls.folders, // URL for fetching folders
                // Lazy-load each folder's contents
                // Each row stores its url for fetching the folders it contains
                fetchUrl: function(row) {
                    return row.urls.folders;
                }
            });
        };

        /**
         * Toggles the visibility of the folder picker.
         */
        self.togglePicker = function() {
            // Toggle visibility of folder picker
            var show = !self.showPicker();
            self.showPicker(show);
            if (show) {
                self.activatePicker();
            } else {
                self.selected(null);
            }
        };
    };

    // Public API

    function DropboxConfigManager(selector, url, folderPicker) {
        var self = this;
        self.url = url;
        self.folderPicker = folderPicker;
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                self.viewModel = new ViewModel(response.result, folderPicker);
                $.osf.applyBindings(self.viewModel, selector);
            },
            error: function(xhr, textStatus, error) {
                console.log(textStatus);
                console.log(error);
                bootbox.alert({
                    title: 'Dropbox Error',
                    message: 'An error occurred while connecting with Dropbox. Please try again later.'
                });
            }
        });
    }

    // Export
    window.DropboxConfigManager = DropboxConfigManager;
    $script.done('dropboxConfigManager');
});

