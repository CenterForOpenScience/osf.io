/**
 * Module that controls the Dropbox node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'js/folderPicker', 'osfutils'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('folderPicker', function() {
            global.DropboxNodeConfig  = factory(ko, jQuery, FolderPicker);
            $script.done('dropboxNodeConfig');
        });
    } else {
        global.DropboxNodeConfig  = factory(ko, jQuery, FolderPicker);
    }
}(this, function(ko, $, FolderPicker) {
    'use strict';

    /**
     * Knockout view model for the Dropbox node settings widget.
     */
    var ViewModel = function(url, folderPicker) {
        var self = this;
        // Auth information
        self.nodeHasAuth = ko.observable(false);
        self.userHasAuth = ko.observable(false);
        // Currently linked folder, an Object of the form {name: ..., path: ...}
        self.folder = ko.observable({});
        self.ownerName = ko.observable('');
        self.urls = ko.observable({});
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');
        // Whether or not folder picker is displayed
        self.showPicker = ko.observable(false);
        // CSS selector for the folder picker div
        self.folderPicker = folderPicker;
        // Currently selected folder, an Object of the form {name: ..., path: ...}
        self.selected = ko.observable(null);
        // Whether the initial data has been fetched form the server. Used for
        // error handling.
        self.loaded = ko.observable(false);

        /**
         * Update the view model from data returned from the server.
         */
        self.updateFromData = function(data) {
            self.ownerName(data.ownerName);
            self.nodeHasAuth(data.nodeHasAuth);
            self.userHasAuth(data.userHasAuth);
            self.folder(data.folder);
            self.urls(data.urls);
        };

        self.fetchFromServer = function() {
            $.ajax({
                url: url, type: 'GET', dataType: 'json',
                success: function(response) {
                    self.updateFromData(response.result);
                    self.loaded(true);
                },
                error: function(xhr, textStatus, error) {
                    console.error(textStatus); console.error(error);
                    self.changeMessage('Could not retrieve Dropbox settings at ' +
                        'this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:contact@cos.io">contact@cos.io</a>.',
                        'text-warning');
                }
            });
        };

        // Initial fetch from server
        self.fetchFromServer();


        /**
         * Whether or not to show the Import Access Token Button
         */
        self.showImport = ko.computed(function() {
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loaded();
            return userHasAuth && !nodeHasAuth && loaded;
        });

        /** Whether or not to show the full settings pane. */
        self.showSettings = ko.computed(function() {
            return self.nodeHasAuth();
        });

        /** Whether or not to show the Create Access Token button */
        self.showTokenCreateButton = ko.computed(function() {
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loaded();
            return !userHasAuth && !nodeHasAuth && loaded;
        });

        /** Computed functions for the linked and selected folders' display text.*/

        self.folderName = ko.computed(function() {
            // Invoke the observables to ensure dependency tracking
            var nodeHasAuth = self.nodeHasAuth();
            var folder = self.folder();
            return (nodeHasAuth && folder) ? folder.name : '';
        });

        self.selectedFolderName = ko.computed(function() {
            var userHasAuth = self.userHasAuth();
            var selected = self.selected();
            return (userHasAuth && selected) ? selected.name : '';
        });

        function onSubmitSuccess(response) {
            self.changeMessage('Successfully linked "' + self.selected().name +
                '". Go to the <a href="' +
                self.urls().files + '">Files page</a> to view your files.',
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
            $.osf.putJSON(self.urls().config, ko.toJS(self),
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
                url: self.urls().deauthorize,
                type: 'DELETE',
                success: function() {
                    // Update observables
                    self.nodeHasAuth(false);
                    self.selected(null);
                    self.showPicker(false);
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

        // Callback for when PUT request to import user access token
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
                        return $.osf.putJSON(self.urls().importAuth, {},
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
        var progBar = '#dropboxProgBar';
        self.activatePicker = function() {
            // Show progress bar
            var $progBar = $(progBar);
            $progBar.show();
            $(self.folderPicker).folderpicker({
                onPickFolder: onPickFolder,
                // Fetch Dropbox folders with AJAX
                data: self.urls().folders, // URL for fetching folders
                // Lazy-load each folder's contents
                // Each row stores its url for fetching the folders it contains
                fetchUrl: function(row) {
                    return row.urls.folders;
                },
                ajaxOptions: {
                    error: function(xhr, textStatus, error) {
                        $progBar.hide();
                        console.error('Could not fetch Dropbox folders.');
                        console.error(textStatus);
                        console.error(error);
                        self.changeMessage('Could not get folders. Please try again later.', 'text-warning');
                    }
                },
                progBar: progBar
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
    function DropboxNodeConfig(selector, url, folderPicker) {
        var self = this;
        self.url = url;
        self.folderPicker = folderPicker;
        self.viewModel = new ViewModel(url, folderPicker);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return DropboxNodeConfig;
}));
