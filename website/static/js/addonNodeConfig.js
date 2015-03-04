/**
 * Module that controls the addon node settings. Includes Knockout view-model
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

var FolderPickerViewModel = function(addonName, url, selector, folderPicker, opts) {
    var self = this;

    self.url = url;
    self.addonName = addonName;
    self.selector = selector;
    // Auth information
    self.nodeHasAuth = ko.observable(false);
    // whether current user is authorizer of the addon
    self.userIsOwner = ko.observable(false);
    // whether current user has an auth token
    self.userHasAuth = ko.observable(false);
    // whether the auth token is valid
    self.validCredentials = ko.observable(true);
    // Currently linked folder, an Object of the form {name: ..., path: ..., id: ...}
    self.folder = ko.observable({
        name: null,
        path: null,
        id: null
    });
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

    // Whether the folders have been loaded from the API
    self.loadedFolders = ko.observable(false);

    self.messages = {
        INVALID_CRED_OWNER: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' settings at ' +
                'this time. The ' + self.addonName + ' addon credentials may no longer be valid.' +
                ' Try deauthorizing and reauthorizing ' + self.addonName + ' on your <a href="' +
                self.urls().settings + '">account settings page</a>.';
        }),
        INVALID_CRED_NOT_OWNER: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' settings at ' +
                'this time. The ' + self.addonName + ' addon credentials may no longer be valid.' +
                ' Contact ' + self.ownerName() + ' to verify.';
        }),
        CANT_RETRIEVE_SETTINGS: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' settings at ' +
                'this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        }),
        UPDATE_ACCOUNTS_ERROR: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' account list at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        }),
        DEAUTHORIZE_SUCCESS: ko.pureComputed(function() {
            return 'Deauthorized ' + self.addonName + '.';
        }),
        DEAUTHORIZE_FAIL: ko.pureComputed(function() {
            return 'Could not deauthorize because of an error. Please try again later.';
        }),
        CONNECT_ACCOUNT_SUCCESS: ko.pureComputed(function() {
            return 'Successfully created a ' + self.addonName + ' Access Token';
        }),
        SUBMIT_SETTINGS_SUCCESS: ko.pureComputed(function() {
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            return 'Successfully linked "' + $osf.htmlEscape(self.selected().name) + '". Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.';
        }),
        SUBMIT_SETTINGS_ERROR: ko.pureComputed(function() {
            return 'Could not change settings. Please try again later.';
        }),
        CONFIRM_DEAUTH: ko.pureComputed(function() {
            return 'Are you sure you want to remove this ' + self.addonName + ' authorization?';
        }),
        CONFIRM_AUTH: ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your ' + self.addonName + ' access token?';
        }),
        TOKEN_IMPORT_SUCCESS: ko.pureComputed(function() {
            return 'Successfully imported access token from profile.';
        }),
        TOKEN_IMPORT_ERROR: ko.pureComputed(function() {
            return 'Error occurred while importing access token.';
        }),
        CONNECT_ERROR: ko.pureComputed(function() {
            return 'Could not connect to ' + self.addonName + ' at this time. Please try again later.';
        })
    };

    // List of contributor emails as a comma-separated values
    self.emailList = ko.pureComputed(function() {
        return self.emails().join([', ']);
    });
    self.disableShare = ko.pureComputed(function() {
        return !self.urls().share;
    });

    /**
     *  Whether or not to show the Import Access Token Button
     */
    self.showImport = ko.pureComputed(function() {
        // Invoke the observables to ensure dependency tracking
        var userHasAuth = self.userHasAuth();
        var nodeHasAuth = self.nodeHasAuth();
        var loaded = self.loadedSettings();
        return userHasAuth && !nodeHasAuth && loaded;
    });

    /** Whether or not to show the full settings pane. */
    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth();
    });

    /** Whether or not to show the Create Access Token button */
    self.showTokenCreateButton = ko.pureComputed(function() {
        // Invoke the observables to ensure dependency tracking
        var userHasAuth = self.userHasAuth();
        var nodeHasAuth = self.nodeHasAuth();
        var loaded = self.loadedSettings();
        return !userHasAuth && !nodeHasAuth && loaded;
    });

    /** Computed functions for the linked and selected folders' display text.*/
    self.folderName = ko.pureComputed(function() {
        // Invoke the observables to ensure dependency tracking
        var nodeHasAuth = self.nodeHasAuth();
        var folder = self.folder();
        return (nodeHasAuth && folder) ? folder.name : '';
    });

    self.selectedFolderName = ko.pureComputed(function() {
        var userIsOwner = self.userIsOwner();
        var selected = self.selected();
        return (userIsOwner && selected) ? selected.name : '';
    });

    self.selectedFolderType = ko.computed(function() {
        var userHasAuth = self.userHasAuth();
        var selected = self.selected();
        return (userHasAuth && selected) ? selected.type : '';
    });

    // Overrides
    self.options = {
        onPickFolder: function(evt, item) {
            evt.preventDefault();
            var name = item.data.path !== '/' ? item.data.path : '/ (Full ' + self.addonName + ')';
            self.selected({
                name: name,
                path: item.data.path
            });
            return false; // Prevent event propagation
        }
    };
    // Overrides
    self.options = $.extend(self.options, opts);

    // Initial fetch from server
    self.fetchFromServer();
};

/**
 *  Update the view model from data returned from the server.
 */
FolderPickerViewModel.prototype.updateFromData = function(data) {
    this.ownerName(data.ownerName);
    this.nodeHasAuth(data.nodeHasAuth);
    this.userIsOwner(data.userIsOwner);
    this.userHasAuth(data.userHasAuth);
    this.validCredentials(data.validCredentials);
    // Make sure folder has name and path properties defined
    this.folder(data.folder || {
        name: null,
        path: null,
        id: null
    });
    this.urls(data.urls);
};

FolderPickerViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var request = $.ajax({
            url: this.url,
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            self.updateFromData(response.result);
            self.loadedSettings(true);
            if (!self.validCredentials()) {
                if (self.userIsOwner()) {
                    self.changeMessage(self.messages.INVALID_CRED_OWNER(), 'text-warning');
                } else {
                    self.changeMessage(self.message.INVALID_CRED_NOT_OWNER(), 'text-warning');
                }
            }
        })
        .fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.CANT_RETRIEVE_SETTINGS(), 'text-warning');
            Raven.captureMessage('Could not GET ' + self.addonName + ' settings', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
        });
    return request;
};

FolderPickerViewModel.prototype.toggleShare = function() {
    if (this.currentDisplay() === this.SHARE) {
        this.currentDisplay(null);
    } else {
        // Clear selection
        this.cancelSelection();
        this.currentDisplay(this.SHARE);
        this.activateShare();
    }
};

FolderPicker.prototype.activateShare = function() {
    var self = this;

    function onGetEmailsSuccess(response) {
        var emails = response.result.emails;
        self.emails(emails);
        self.loadedEmails(true);
    }

    if (!this.loadedEmails()) {
        $.ajax({
            url: self.urls().emails,
            type: 'GET',
            dataType: 'json',
            success: onGetEmailsSuccess
        });
    }
    var $copyBtn = $('#copyBtn');
    new ZeroClipboard($copyBtn);
};

/**
 * Send a PUT request to change the linked folder.
 */
FolderPickerViewModel.prototype.submitSettings = function() {
    var self = this;

    function onSubmitSuccess(response) {
        self.changeMessage(self.messages.SUBMIT_SETTINGS_SUCCESS(), 'text-success', 5000);
        // Update folder in ViewModel
        self.folder(response.result.folder);
        self.urls(response.result.urls);
        self.cancelSelection();
    }

    function onSubmitError() {
        self.changeMessage(self.messages.SUBMIT_SETTINGS_ERROR(), 'text-danger');
    }

    $osf.putJSON(self.urls().config, ko.toJS(self))
        .done(onSubmitSuccess)
        .fail(onSubmitError);
};

/**
 *  Must be used to update radio buttons and knockout view model simultaneously
 */
FolderPickerViewModel.prototype.cancelSelection = function() {
    this.selected(null);
};

/** Change the flashed message. */
FolderPickerViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
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

/** Pop up a confirmation to deauthorize this node.
 *   Send DELETE request if confirmed.
 */
FolderPickerViewModel.prototype.deauthorize = function() {
    var self = this;

    //  Send DELETE request to deauthorize this node.
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
            self.changeMessage(self.messages.DEAUTHORIZE_SUCCESS(), 'text-warning', 3000);
        }).fail(function(xhr, status, error) {
            self.changeMessage(self.messages.DEAUTHORIZE_FAIL(), 'text-danger');
            Raven.captureMessage('Failed to deauthorize ' + self.addonName + '.', {
                url: url,
                status: status,
                error: error
            });
        });
    }

    bootbox.confirm({
        title: 'Deauthorize ' + self.addonName + '?',
        message: self.messages.CONFIRM_DEAUTH(),
        callback: function(confirmed) {
            if (confirmed) {
                return sendDeauth();
            }
        }
    });
};


/**
 * Send PUT request to import access token from user profile.
 */
FolderPickerViewModel.prototype.importAuth = function() {
    var self = this;

    // Callback for when PUT request to import user access token
    function onImportSuccess(response) {
        var msg = response.message || self.messages.TOKEN_IMPORT_SUCCESS();
        // Update view model based on response
        self.changeMessage(msg, 'text-success', 3000);
        self.updateFromData(response.result);
        self.activatePicker();
    }

    function onImportError(xhr, status, error) {
        self.changeMessage(self.messages.TOKEN_IMPORT_ERROR(), 'text-danger');
        Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
            xhr: xhr,
            status: status,
            error: error
        });
    }

    bootbox.confirm({
        title: 'Import ' + self.addonName + ' Access Token?',
        message: self.messages.CONFIRM_AUTH(),
        callback: function(confirmed) {
            if (confirmed) {
                return $osf.putJSON(self.urls().importAuth, {})
                    .done(onImportSuccess)
                    .fail(onImportError);
            }
        }
    });
};

/**
 *  Activates the HGrid folder picker.
 */
FolderPickerViewModel.prototype.activatePicker = function() {
    var self = this;

    self.currentDisplay(self.PICKER);
    // Only load folders if they haven't already been requested
    if (!self.loadedFolders()) {
        // Show loading indicator
        self.loading(true);
        $(self.folderPicker).folderpicker({
            onPickFolder: self.options.onPickFolder.bind(self),
            initialFolderPath: self.folder().path || '',
            // Fetch folders with AJAX
            filesData: self.urls().folders, // URL for fetching folders
            // Lazy-load each folder's contents
            // Each row stores its url for fetching the folders it contains
            resolveLazyloadUrl: function(item) {
                return item.data.urls.folders;
            },
            oddEvenClass: {
                odd: 'addon-folderpicker-odd',
                even: 'addon-folderpicker-even'
            },
            ajaxOptions: {
                error: function(xhr, textStatus, error) {
                    self.loading(false);
                    self.changeMessage(self.messages.CONNECT_ERROR(), 'text-warning');
                    Raven.captureMessage('Could not GET get ' + self.addonName + ' contents.', {
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
FolderPickerViewModel.prototype.togglePicker = function() {
    // Toggle visibility of folder picker
    var shown = this.currentDisplay() === this.PICKER;
    if (!shown) {
        this.currentDisplay(this.PICKER);
        this.activatePicker();
    } else {
        this.currentDisplay(null);
        // Clear selection
        this.cancelSelection();
    }
};

// Public API
function AddonNodeConfig(addonName, selector, url, folderPicker, opts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    if (typeof opts === 'undefined') {
        opts = {};
    }
    self.viewModel = new FolderPickerViewModel(addonName, url, selector, folderPicker, opts);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = AddonNodeConfig;
