var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var FolderPicker = require('folderpicker');
var $osf = require('osfHelpers');
var ctx = window.contextVars;

ko.punches.enableAll();
/**
 * Knockout view model for citations node settings widget.
 */
var CitationsFolderPickerViewModel = function(name, url, selector, folderPicker) {
    var self = this;

    self.url = url;
    self.properName = name.charAt(0).toUpperCase() + name.slice(1);
    self.selector = selector;
    // CSS selector for the folder picker div
    self.folderPicker = folderPicker;

    // DEFAULTS
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
    // Currently linked folder, an Object of the form {name: ..., id: ...}
    self.folder = ko.observable({
        name: '',
        id: ''
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
    // Currently selected folder name
    self.selected = ko.observable(false);
    self.loading = ko.observable(false);
    // Whether the initial data has been fetched form the server. Used for
    // error handling.
    self.loadedSettings = ko.observable(false);
    // Whether the folders have been loaded from the API
    self.loadedFolders = ko.observable(false);

    self.messages = {
        INVALID_CRED_OWNER: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.properName + ' settings at ' +
                'this time. The ' + self.properName + ' addon credentials may no longer be valid.' +
                ' Try deauthorizing and reauthorizing ' + self.properName + ' on your <a href="' +
                self.urls().settings + '">account settings page</a>.';
        }),
        INVALID_CRED_NOT_OWNER: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.properName + ' settings at ' +
                'this time. The ' + self.properName + ' addon credentials may no longer be valid.' +
                ' Contact ' + self.ownerName() + ' to verify.';
        }),
        CANT_RETRIEVE_SETTINGS: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.properName + ' settings at ' +
                'this time. Please refresh ' +
                'the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        }),
        UPDATE_ACCOUNTS_ERROR: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.properName + ' account list at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        }),
        DEAUTHORIZE_SUCCESS: ko.pureComputed(function() {
            return 'Deauthorized ' + self.properName + '.';
        }),
        DEAUTHORIZE_FAIL: ko.pureComputed(function() {
            return 'Could not deauthorize because of an error. Please try again later.';
        }),
        CONNECT_ACCOUNT_SUCCESS: ko.pureComputed(function() {
            return 'Successfully created a ' + self.properName + ' Access Token';
        }),
        SUBMIT_SETTINGS_SUCCESS: ko.pureComputed(function() {
            var overviewURL = window.contextVars.node.urls.web;
            return 'Successfully linked "' + $osf.htmlEscape(self.folder()) + '". Go to the <a href="' +
                overviewURL + '">Overview page</a> to view your citations.';
        }),
        SUBMIT_SETTINGS_ERROR: ko.pureComputed(function() {
            return 'Could not change settings. Please try again later.';
        }),
        CONFIRM_DEAUTH: ko.pureComputed(function() {
            return 'Are you sure you want to remove this ' + self.properName + ' authorization?';
        }),
        CONFIRM_AUTH: ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your ' + self.properName + ' access token?';
        }),
        TOKEN_IMPORT_ERROR: ko.pureComputed(function() {
            return 'Error occurred while importing access token.';
        }),
        CONNECT_ERROR: ko.pureComputed(function() {
            return 'Could not connect to ' + self.properName + ' at this time. Please try again later.';
        })
    };

    /**
     * Whether or not to show the Import Access Token Button
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
        var nodeHasAuth = self.nodeHasAuth();
        var folder = self.folder();
        return (nodeHasAuth && folder) ? folder.name : '';
    });

    self.selectedFolderName = ko.pureComputed(function() {
        var userIsOwner = self.userIsOwner();
        var selected = self.selected();
        return (userIsOwner && selected) ? selected.name : '';
    });


    // Initial fetch from server
    self.fetchFromServer();
};


/** Change the flashed message. */
CitationsFolderPickerViewModel.prototype.changeMessage = function(text, css, timeout) {
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

/**
 * Update the view model from data returned from the server.
 */
CitationsFolderPickerViewModel.prototype.updateFromData = function(data) {
    var self = this;
    self.ownerName(data.ownerName);
    self.nodeHasAuth(data.nodeHasAuth);
    self.userIsOwner(data.userIsOwner);
    self.userHasAuth(data.userHasAuth);
    self.userAccountId(data.userAccountId);
    self.folder(data.folder || 'None');
    self.urls(data.urls);
    self.validCredentials(data.validCredentials);
};

CitationsFolderPickerViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var request = $.ajax({
        url: self.url,
        type: 'GET',
        dataType: 'json'
    });

    request.done(function(response) {
        self.updateFromData(response);
        self.loadedSettings(true);
        if (!self.validCredentials()) {
            if (self.userIsOwner()) {
                self.changeMessage(self.messages.INVALID_CRED_OWNER(), 'text-warning');
            } else {
                self.changeMessage(self.messages.INVALID_CRED_NOT_OWNER(), 'text-warning');
            }
        }
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.CANT_RETRIEVE_SETTINGS(), 'text-warning');
        Raven.captureMessage('Could not GET ' + self.properName + 'settings', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
    });
};


CitationsFolderPickerViewModel.prototype.updateAccounts = function(callback) {
    var self = this;
    var request = $.get(self.urls().accounts);
    request.done(function(data) {
        self.accounts(data.accounts.map(function(account) {
            return {
                name: account.display_name,
                id: account.id
            };
        }));
        callback();
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.UPDATE_ACCOUNTS_ERROR(), 'text-warning');
        Raven.captureMessage('Could not GET ' + self.properName + ' accounts for user', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
    });
};
/**
 * Allows a user to create a Menedeley access token from the nodeSettings page
 */
CitationsFolderPickerViewModel.prototype.connectAccount = function() {
    var self = this;

    window.oauthComplete = function(res) {
        // Update view model based on response
        self.changeMessage(self.messages.CONNECT_ACCOUNT_SUCCESS(), 'text-success', 3000);
        self.updateAccounts(function() {
            $osf.postJSON(
                self.urls().importAuth, {
                    external_account_id: self.accounts()[0].id
                }
            ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
        });
    };
    window.open(self.urls().auth);
};

CitationsFolderPickerViewModel.prototype.connectExistingAccount = function(account_id) {
    var self = this;

    $osf.postJSON(
        self.urls().importAuth, {
            external_account_id: account_id
        }
    ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
};


/**
 * Send a PUT request to change the linked folder.
 */
CitationsFolderPickerViewModel.prototype.submitSettings = function() {
    var self = this;

    function onSubmitSuccess(response) {
        self.folder(self.selected().name);
        self.changeMessage(self.messages.SUBMIT_SETTINGS_SUCCESS(), 'text-success', 5000);
        self.cancelSelection();
    }

    function onSubmitError() {
        self.changeMessage(self.messages.SUBMIT_SETTINGS_ERROR(), 'text-danger');
    }


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
CitationsFolderPickerViewModel.prototype.cancelSelection = function() {
    this.selected(null);
};

/** Pop up a confirmation to deauthorize addon from this node.
 *  Send DELETE request if confirmed.
 */
CitationsFolderPickerViewModel.prototype.deauthorize = function() {
    var self = this;

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
            self.changeMessage(self.messages.DEAUTHORIZE_SUCCESS(), 'text-warning', 3000);
        });

        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.DEAUTHORIZE_FAIL(), 'text-danger');
            Raven.captureMessage('Could not deauthorize ' + self.properName + ' account from node', {
                url: self.urls().deauthorize,
                textStatus: textStatus,
                error: error
            });
        });

        return request;
    }

    bootbox.confirm({
        title: 'Deauthorize ' + self.properName + '?',
        message: self.messages.CONFIRM_DEAUTH(),
        callback: function(confirmed) {
            if (confirmed) {
                return sendDeauth();
            }
        }
    });
};


// Callback for when PUT request to import user access token
CitationsFolderPickerViewModel.prototype.onImportSuccess = function(response) {
    var self = this;

    var msg = response.message || 'Successfully imported access token from profile.';
    // Update view model based on response
    self.changeMessage(msg, 'text-success', 3000);
    self.updateFromData(response.result);
    self.activatePicker();
};

CitationsFolderPickerViewModel.prototype.onImportError = function(xhr, textStatus, error) {
    var self = this;

    self.changeMessage(self.messages.TOKEN_IMPORT_ERROR(), 'text-danger');
    Raven.captureMessage('Failed to import ' + self.properName + ' access token', {
        url: self.urls().importAuth,
        textStatus: textStatus,
        error: error
    });
};

/**
 * Send PUT request to import access token from user profile.
 */
CitationsFolderPickerViewModel.prototype.importAuth = function() {
    var self = this;

    self.updateAccounts(function() {
        if (self.accounts().length > 1) {
            bootbox.prompt({
                title: 'Choose ' + self.properName + ' Access Token to Import',
                inputType: 'select',
                inputOptions: ko.utils.arrayMap(
                    self.accounts(),
                    function(item) {
                        return {
                            text: item.name,
                            value: item.id
                        };
                    }
                ),
                value: self.accounts()[0].id,
                callback: (self.connectExistingAccount.bind(self))
            });
        } else {
            bootbox.confirm({
                title: 'Import ' + self.properName + ' Access Token?',
                message: self.messages.CONFIRM_AUTH(),
                callback: function(confirmed) {
                    if (confirmed) {
                        self.connectExistingAccount.call(self, (self.accounts()[0].id));
                    }
                }
            });
        }
    });
};

/**
 * Activates the HGrid folder picker.
 */
CitationsFolderPickerViewModel.prototype.activatePicker = function() {
    var self = this;


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

    self.currentDisplay(self.PICKER);
    // Only load folders if they haven't already been requested
    if (!self.loadedFolders()) {
        // Show loading indicator
        self.loading(true);
        $(self.folderPicker).folderpicker({
            onPickFolder: onPickFolder,
            initialFolderPath: '',
            // Fetch folders with AJAX
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
                odd: 'addon-folderpicker-odd',
                even: 'addon-folderpicker-even'
            },
            ajaxOptions: {
                error: function(xhr, textStatus, error) {
                    self.loading(false);
                    self.changeMessage(self.messages.CONNECT_ERROR(), 'text-warning');
                    Raven.captureMessage('Could not GET get ' + self.properName + ' contents.', {
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
CitationsFolderPickerViewModel.prototype.togglePicker = function() {
    var self = this;

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

module.exports = CitationsFolderPickerViewModel;
