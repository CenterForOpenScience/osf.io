/**
* Module that controls the Box node settings. Includes Knockout view-model
* for syncing data, and HGrid-folderpicker for selecting a folder.
*/
'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var FolderPicker = require('folderpicker');
var ZeroClipboard = require('zeroclipboard');
ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
var $osf = require('osfHelpers');

ko.punches.enableAll();
/**
*  Knockout view model for the Box node settings widget.
*/
var ViewModel = function(url, selector, folderPicker) {
    var self = this;
    self.selector = selector;
    // Auth information
    self.nodeHasAuth = ko.observable(false);
    // whether current user is authorizer of the addon
    self.userIsOwner = ko.observable(false);
    // whether current user has an auth token
    self.userHasAuth = ko.observable(false);
    // whether the auth token is valid
    self.validCredentials = ko.observable(true);
    // Currently linked folder, an Object of the form {name: ..., path: ...}
    self.folder = ko.observable({name: null, path: null, id: null});
    self.ownerName = ko.observable('');
    self.urls = ko.observable({});
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');
    // Display names
    self.PICKER = 'picker';
    self.SHARE = 'share';
    // Current folder display
    self.currentDisplay = ko.observable(null);
    // CSS selector for the folder picker div
    self.folderPicker = folderPicker;
    // Currently selected folder, an Object of the form {name: ..., path: ...}
    self.selected = ko.observable(null);
    // Emails of contributors, can only be populated by activating the share dialog
    self.emails = ko.observableArray([]);
    self.loading = ko.observable(false);
    // Whether the initial data has been fetched form the server. Used for
    // error handling.
    self.loadedSettings = ko.observable(false);
    // Whether the contributor emails have been loaded from the server
    self.loadedEmails = ko.observable(false);

    // Whether the box folders have been loaded from the server/Box API
    self.loadedFolders = ko.observable(false);

    // List of contributor emails as a comma-separated values
    self.emailList = ko.computed(function() {
        return self.emails().join([', ']);
    });

    self.disableShare = ko.computed(function() {
        return !self.urls().share;
    });

    /**
    *  Update the view model from data returned from the server.
    */
    self.updateFromData = function(data) {
        self.ownerName(data.ownerName);
        self.nodeHasAuth(data.nodeHasAuth);
        self.userIsOwner(data.userIsOwner);
        self.userHasAuth(data.userHasAuth);
        self.validCredentials(data.validCredentials);
        // Make sure folder has name and path properties defined
        self.folder(data.folder || {name: null, path: null, id: null});
        self.urls(data.urls);
    };

    self.fetchFromServer = function() {
        var request = $.ajax({
            url: url, type: 'GET', dataType: 'json',
        })
        .done(function(response) {
            self.updateFromData(response.result);
            self.loadedSettings(true);
            if (!self.validCredentials()){
                if (self.userIsOwner()) {
                    self.changeMessage('Could not retrieve Box settings at ' +
                    'this time. The Box addon credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing Box on your <a href="' +
                        self.urls().settings + '">account settings page</a>.',
                    'text-warning');
                } else {
                    self.changeMessage('Could not retrieve Box settings at ' +
                    'this time. The Box addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.',
                    'text-warning');
                }
            }
        })
        .fail(function(xhr, textStatus, error) {
            self.changeMessage('Could not retrieve Box settings at ' +
                'this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.',
                'text-warning');
            Raven.captureMessage('Could not GET Box settings', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
        return request;
    };

    // Initial fetch from server
    self.fetchFromServer();

    self.toggleShare = function() {
        if (self.currentDisplay() === self.SHARE) {
            self.currentDisplay(null);
        } else {
            // Clear selection
            self.cancelSelection();
            self.currentDisplay(self.SHARE);
            self.activateShare();
        }
    };


    function onGetEmailsSuccess(response) {
        var emails = response.result.emails;
        self.emails(emails);
        self.loadedEmails(true);
    }

    self.activateShare = function() {
        if (!self.loadedEmails()) {
            $.ajax({
                url: self.urls().emails, type: 'GET', dataType: 'json',
                success: onGetEmailsSuccess
            });
        }
        var $copyBtn = $('#copyBtn');
        new ZeroClipboard($copyBtn);
    };


    /**
    *  Whether or not to show the Import Access Token Button
    */
    self.showImport = ko.computed(function() {
        // Invoke the observables to ensure dependency tracking
        var userHasAuth = self.userHasAuth();
        var nodeHasAuth = self.nodeHasAuth();
        var loaded = self.loadedSettings();
        return userHasAuth && !nodeHasAuth && loaded;
    });

    /** Whether or not to show the full settings pane. */
    self.showSettings = ko.computed(function() {
        return self.nodeHasAuth();
    });

    /** Whether or not to show the Create Access Token button */
    self.showTokenCreateButton = ko.computed(function() {
        // Invoke the observables to ensure dependency tracking
        var userHasAuth = self.userHasAuth();
        var nodeHasAuth = self.nodeHasAuth();
        var loaded = self.loadedSettings();
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
        var userIsOwner = self.userIsOwner();
        var selected = self.selected();
        return (userIsOwner && selected) ? selected.name : '';
    });

    function onSubmitSuccess(response) {
        self.changeMessage('Successfully linked "' + self.selected().name +
            '". Go to the <a href="' +
            self.urls().files + '">Files page</a> to view your files.',
            'text-success', 5000);
        // Update folder in ViewModel
        self.folder(response.result.folder);
        self.urls(response.result.urls);
        self.cancelSelection();
    }

    function onSubmitError() {
        self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
    }

    /**
    * Send a PUT request to change the linked Box folder.
    */
    self.submitSettings = function() {
        $osf.putJSON(self.urls().config, ko.toJS(self))
            .done(onSubmitSuccess)
            .fail(onSubmitError);
    };

    /**
    *  Must be used to update radio buttons and knockout view model simultaneously
    */
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
    *  Send DELETE request to deauthorize this node.
    */
    function sendDeauth() {
        var url = self.urls().deauthorize;
        return $.ajax({
            url: url,
            type: 'DELETE',
        }).done(function() {
            // Update observables
            self.nodeHasAuth(false);
            self.cancelSelection();
            self.currentDisplay(null);
            self.changeMessage('Deauthorized Box.', 'text-warning', 3000);
        }).fail(function(xhr, status, error) {
            self.changeMessage('Could not deauthorize because of an error. Please try again later.',
                'text-danger');
            Raven.captureMessage('Failed to deauthorize Box.', {
                url: url, status: status, error: error
            });
        });
    }

    /** Pop up a confirmation to deauthorize Box from this node.
    *   Send DELETE request if confirmed.
    */
    self.deauthorize = function() {
        bootbox.confirm({
            title: 'Deauthorize Box?',
            message: 'Are you sure you want to remove this Box authorization?',
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
        self.activatePicker();
    }

    function onImportError(xhr, status, error) {
        self.message('Error occurred while importing access token.');
        self.messageClass('text-danger');
        Raven.captureMessage('Failed to import Box access token.', {
            xhr: xhr, status: status, error: error
        });
    }

    /**
        * Send PUT request to import access token from user profile.
        */
    self.importAuth = function() {
        bootbox.confirm({
            title: 'Import Box Access Token?',
            message: 'Are you sure you want to authorize this project with your Box access token?',
            callback: function(confirmed) {
                if (confirmed) {
                    return $osf.putJSON(self.urls().importAuth, {})
                        .done(onImportSuccess)
                        .fail(onImportError);
                }
            }
        });
    };

    /** Callback for chooseFolder action.
    *   Just changes the ViewModel's self.selected observable to the selected
    *   folder.
    */
    function onPickFolder(evt, item) {
            evt.preventDefault();
            self.selected({name: 'Box' + item.data.path, path: item.data.path, id: item.data.id});
            return false; // Prevent event propagation
        }

    /**
    *  Activates the HGrid folder picker.
    */
    self.activatePicker = function() {
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            // Show loading indicator
            self.loading(true);
            $(self.folderPicker).folderpicker({
                onPickFolder: onPickFolder,
                initialFolderName : self.folder().path,
                initialFolderPath : 'All Files',
                // Fetch Box folders with AJAX
                filesData: self.urls().folders, // URL for fetching folders
                // Lazy-load each folder's contents
                // Each row stores its url for fetching the folders it contains
                resolveLazyloadUrl : function(item){
                    if (item.data.urls) {
                        return item.data.urls.folders;
                    }
                    return null;
                },
                oddEvenClass : {
                    odd : 'box-folderpicker-odd',
                    even : 'box-folderpicker-even'
                },
                ajaxOptions: {
                    error: function(xhr, textStatus, error) {
                        self.loading(false);
                        self.changeMessage('Could not connect to Box at this time. ' +
                                            'Please try again later.', 'text-warning');
                        Raven.captureMessage('Could not GET get Box contents.', {
                            textStatus: textStatus,
                            error: error
                        });
                    }
                },
                folderPickerOnload: function() {
                    // Hide loading indicator
                    self.loading(false);
                    // Set flag to prevent repeated requests
                    self.loadedFolders(true);
                }
            });
        }
    };

    /**
    *  Toggles the visibility of the folder picker.
    */
    self.togglePicker = function() {
        // Toggle visibility of folder picker
        var shown = self.currentDisplay() === self.PICKER;
        if (!shown) {
            self.currentDisplay(self.PICKER);
            self.activatePicker();
        } else {
            self.currentDisplay(null);
            // Clear selection
            self.cancelSelection();
        }
    };
};

// Public API
function BoxNodeConfig(selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new ViewModel(url, selector, folderPicker);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = BoxNodeConfig;
