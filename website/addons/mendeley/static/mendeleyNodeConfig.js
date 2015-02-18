/**
 * Module that controls the mendeley node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var FolderPicker = require('folderpicker');
var $osf = require('osfHelpers');

ko.punches.enableAll();
/**
 * Knockout view model for the mendeley node settings widget.
 */
var ViewModel = function(url, selector, folderPicker) {
    var self = this;
    self.selector = selector;
    // Accounts
    self.accounts = ko.observableArray([]);
    // Auth information
    self.nodeHasAuth = ko.observable(false);
    // whether current user is authorizer of the addon
    self.userIsOwner = ko.observable(false);
    // whether current user has an auth token
    self.userHasAuth = ko.observable(false);
    // whether the auth token is valid
    self.validCredentials = ko.observable(true);
    self.userAccountId = ko.observable('');
    // Currently linked folder, an Object of the form {name: ..., path: ...}
    self.folder = ko.observable({
        name: null,
        path: null
    });
    self.ownerName = ko.observable('');
    self.urls = ko.observable({});
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');
    // Display names
    self.PICKER = 'picker';
    // Current folder display
    self.currentDisplay = ko.observable(false);
    // CSS selector for the folder picker div
    self.folderPicker = folderPicker;
    // Currently selected folder, an Object of the form {name: ..., path: ...}
    self.selected = ko.observable(null);
    self.loading = ko.observable(false);
    // Whether the initial data has been fetched form the server. Used for
    // error handling.
    self.loadedSettings = ko.observable(false);
    // Whether the contributor emails have been loaded from the server
    self.loadedEmails = ko.observable(false);

    // Whether the mendeley folders have been loaded from the server/mendeley API
    self.loadedFolders = ko.observable(false);

    /**
     * Update the view model from data returned from the server.
     */
    self.updateFromData = function(data) {
        self.ownerName(data.ownerName);
        self.nodeHasAuth(data.nodeHasAuth);
        self.userIsOwner(data.userIsOwner);
        self.userHasAuth(data.userHasAuth);
        self.userAccountId(data.userAccountId);
        // Make sure folder has name and path properties defined
        self.folder(data.folder || 'None');
        self.urls(data.urls);
    };

    self.fetchFromServer = function() {
        var request = $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        });

        request.done(function(response) {
            self.updateFromData(response);
            self.loadedSettings(true);
            /*
            if (!self.validCredentials()){
                if (self.userIsOwner()) {
                    self.changeMessage('Could not retrieve Mendeley settings at ' +
                    'this time. The mendeley addon credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing mendeley on your <a href="' +
                        self.urls().settings + '">account settings page</a>.',
                    'text-warning');
                } else {
                    self.changeMessage('Could not retrieve Mendeley settings at ' +
                    'this time. The mendeley addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.',
                    'text-warning');
                }
            }
            */
        });

        request.fail(function(xhr, textStatus, error) {
            self.changeMessage('Could not retrieve Mendeley settings at ' +
                'this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.',
                'text-warning');
            Raven.captureMessage('Could not GET mendeley settings', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    };

    // Initial fetch from server
    self.fetchFromServer();

    var CitationAccount = function(name, id) {
        this.name = name;
        this.id = id;
    };

    self.updateAccounts = function() {
        var url = '/api/v1/settings/mendeley/accounts/';
        var request = $.get(url);

        request.done(function(data) {
            self.accounts(data.accounts.map(function(account) {
                return new CitationAccount(account.display_name, account.id);
            }));
            $osf.postJSON(
                self.urls().importAuth,
                {external_account_id: self.accounts()[0].id}
            ).then(onImportSuccess, onImportError);
        });

        request.fail(function(xhr, textStatus, error) {
            self.changeMessage('Could not retrieve Mendeley account list at ' +
                'this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.',
                'text-warning');
            Raven.captureMessage('Could not GET mendeley accounts for user', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    };
    /**
     * Allows a user to create a Menedeley access token from the nodeSettings page
     */
    self.connectAccount = function() {
        var self = this;
        window.oauthComplete = function(res) {
            var msg = 'Successfully created a Mendeley Access Token';
            // Update view model based on response
            self.changeMessage(msg, 'text-success', 3000);
            self.updateAccounts();
        };
        window.open('/oauth/connect/mendeley/');
    };

    /**
     * Whether or not to show the Import Access Token Button
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
        self.changeMessage('Successfully linked "' + self.selected().name + '".',
            'text-success', 5000);
        self.folder(self.selected().name);
        self.cancelSelection();
    }

    function onSubmitError() {
        self.changeMessage('Could not change settings. Please try again later.', 'text-danger');
    }

    /**
     * Send a PUT request to change the linked mendeley folder.
     */
    self.submitSettings = function() {
        $osf.putJSON(self.urls().config, {
                external_account_id: self.userAccountId(),
                external_list_id: self.selected().id
            })
            .done(onSubmitSuccess)
            .fail(onSubmitError);
    };

    /**
     * Must be used to update radio buttons and knockout view model simultaneously
     */
    self.cancelSelection = function() {
        self.selected(null);
        // $(selector + ' input[type="radio"]').prop('checked', false);
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
        var request = $.ajax({
            url: self.urls().deauthorize,
            type: 'DELETE'
        });

        request.done(function() {
            // Update observables
            self.nodeHasAuth(false);
            self.cancelSelection();
            self.currentDisplay(null);
            self.changeMessage('Deauthorized mendeley.', 'text-warning', 3000);
        });

        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(
                'Could not deauthorize because of an error. Please try again later.',
                'text-danger'
            );
            Raven.captureMessage('Could not deauthorize mendeley account from node', {
                url: self.urls().deauthorize,
                textStatus: textStatus,
                error: error
            });
        });

        return request;
    }

    /** Pop up a confirmation to deauthorize mendeley from this node.
     *  Send DELETE request if confirmed.
     */
    self.deauthorize = function() {
        bootbox.confirm({
            title: 'Deauthorize mendeley?',
            message: 'Are you sure you want to remove this mendeley authorization?',
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

    function onImportError(xhr, textStatus, error) {
        self.message('Error occurred while importing access token.');
        self.messageClass('text-danger');

        Raven.captureMessage('Failed to import Mendeley access token', {
            url: self.urls().importAuth,
            textStatus: textStatus,
            error: error
        });
    }

    /**
     * Send PUT request to import access token from user profile.
     */
    self.importAuth = function() {
        bootbox.confirm({
            title: 'Import mendeley Access Token?',
            message: 'Are you sure you want to authorize this project with your mendeley access token?',
            callback: function(confirmed) {
                if (confirmed) {
                    return $osf.postJSON(self.urls().importAuth, {
                            external_account_id: self.userAccountId()
                        })
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
        self.selected({
            name: item.data.name,
            id: item.data.id
        });
        return false; // Prevent event propagation
    }

    /**
     * Activates the HGrid folder picker.
     */
    self.activatePicker = function() {
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            // Show loading indicator
            self.loading(true);
            $(self.folderPicker).folderpicker({
                onPickFolder: onPickFolder,
                initialFolderPath: 'mendeley',
                // Fetch mendeley folders with AJAX
                filesData: self.urls().folders,
                // Lazy-load each folder's contents
                // Each row stores its url for fetching the folders it contains
                resolveLazyloadUrl: function(item) {
                    return self.urls().folders + item.data.id + '/?view=folders';
                },
                lazyLoadPreprocess: function(data) {
                    return data.contents.filter(function(item) {
                        return item.kind === 'folder';
                    });
                },
                oddEvenClass: {
                    odd: 'mendeley-folderpicker-odd',
                    even: 'mendeley-folderpicker-even'
                },
                ajaxOptions: {
                    error: function(xhr, textStatus, error) {
                        self.loading(false);
                        self.changeMessage('Could not connect to Mendeley at this time. ' +
                            'Please try again later.', 'text-warning');
                        Raven.captureMessage('Could not GET get Mendeley contents.', {
                            textStatus: textStatus,
                            error: error
                        });
                    }
                },
                folderPickerOnload: function() {
                    // Hide loading indicator
                    self.loading(false);
                }
            });
        }
    };

    /**
     * Toggles the visibility of the folder picker.
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
function MendeleyNodeConfig(selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new ViewModel(url, selector, folderPicker);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = MendeleyNodeConfig;
