/**
 * Abstract module that controls the addon node settings. Includes Knockout view-model
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

var oop = require('js/oop');

ko.punches.enableAll();

var FolderPickerViewModel = oop.defclass({
    constructor: function(addonName, url, selector, folderPicker) {
        /*
         @class ViewModel
         @param {String} addonName: full display name of the addon
         @param {String} url: API url to initially fetch settings
         @param {String} selector: CSS selector for containing div
         @param {String} folderPicker: CSS selector for folderPicker div
         */
        var self = this;
        self.url = url;
        self.addonName = addonName;
        self.selector = selector;
        self.folderPicker = folderPicker;
        // Auth information
        self.nodeHasAuth = ko.observable(false);
        // whether current user has an auth token
        self.userHasAuth = ko.observable(false);
        // whether current user is authorizer of the addon
        self.userIsOwner = ko.observable(false);
        // display name of owner of credentials
        self.ownerName = ko.observable('');
        // whether the auth token is valid
        self.validCredentials = ko.observable(true);
        // current folder
        self.folder = ko.observable({
            name: null,
            id: null,
            path: null
        });
        // set of urls used for API calls internally
        self.urls = ko.observable({});
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');
        // Display names
        self.PICKER = 'picker';
        self.SHARE = 'share';
        // Currently selected folder name
        self.selected = ko.observable(false);
        self.loading = ko.observable(false);
        // Whether the initial data has been fetched form the server. Used for
        // error handling.
        self.loadedSettings = ko.observable(false);
        // Current folder display
        self.currentDisplay = ko.observable(null);
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
                var overviewURL = window.contextVars.node.urls.web;
                return 'Successfully linked "' + $osf.htmlEscape(self.folder().name) + '". Go to the <a href="' +
                    overviewURL + '">Overview page</a> to view your citations.';
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
            TOKEN_IMPORT_ERROR: ko.pureComputed(function() {
                return 'Error occurred while importing access token.';
            }),
            CONNECT_ERROR: ko.pureComputed(function() {
                return 'Could not connect to ' + self.addonName + ' at this time. Please try again later.';
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
            return loaded && !userHasAuth && !nodeHasAuth;
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
            var name = selected.name || 'None';
            return (userIsOwner && selected) ? name : '';
        });
    },
    changeMessage: function(text, css, timeout) {
        /** Change the flashed message. */
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
    },
    _updateCustomFields: function(settings){},  // Abstract method
    updateFromData: function(data) {
        /**
         * Update the view model from data returned from the server.
         */
        var self = this;
        var ret = $.Deferred();
        var applySettings = function(settings){
            self.ownerName(settings.ownerName);
            self.nodeHasAuth(settings.nodeHasAuth);
            self.userIsOwner(settings.userIsOwner);
            self.userHasAuth(settings.userHasAuth);
            self.folder(settings.folder || {
                name: null,
                path: null,
                id: null
            });
            self.urls(settings.urls);
            self._updateCustomFields(settings);
            ret.resolve();
        };
        if (typeof data === 'undefined'){
            self.fetchFromServer()
            .done(applySettings);
        }
        else{
            applySettings(data);
        }
        return ret.promise();
    },
    fetchFromServer: function() {
        var self = this;
        var ret = $.Deferred();
        var request = $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json'
        });
        request.done(function(response) {
            console.log("Loaded " + self.addonName + " settings");
            self.loadedSettings(true);
            ret.resolve(response.result);
        });
        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.CANT_RETRIEVE_SETTINGS(), 'text-warning');
            Raven.captureMessage('Could not GET ' + self.addonName + 'settings', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
            ret.reject(xhr, textStatus, error);
        });
        return ret.promise();
    },
    _serializeSettings: function(){
        return ko.toJS(this);
    },
    submitSettings: function() {
        /**
         * Send a PUT request to change the linked folder.
         */        
        var self = this;
        function onSubmitSuccess(response) {
            // Update folder in ViewModel
            self.folder(response.result.folder);
            self.urls(response.result.urls);
            self.cancelSelection();
            self.changeMessage(self.messages.SUBMIT_SETTINGS_SUCCESS(), 'text-success'); 
        }
        function onSubmitError(xhr, status, error) {
            self.changeMessage(self.messages.SUBMIT_SETTINGS_ERROR(), 'text-danger');
            Raven.captureMessage('Failed to update ' + self.addonName + ' settings.', {
                xhr: xhr,
                status: status,
                error: error
            });
        }
        $osf.putJSON(self.urls().config, self._serializeSettings())
            .done(onSubmitSuccess)
            .fail(onSubmitError);
    },
    _importAuthConfirm: function() {
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
        return $osf.putJSON(self.urls().importAuth, {})
            .done(onImportSuccess)
            .fail(onImportError);
    },
    importAuth: function() {
        /**
         * Send PUT request to import access token from user profile.
         */
        var self = this;
        bootbox.confirm({
            title: 'Import ' + self.addonName + ' Access Token?',
            message: self.messages.CONFIRM_AUTH(),
            callback: function(confirmed) {
                if (confirmed) {
                    self._importAuthConfirm();
                }
            }
        });
    },
    _deauthorizeConfirm: function(){
        /**
         * Send DELETE request to deauthorize this node.
         */
        var self = this;
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
            Raven.captureMessage('Could not deauthorize ' + self.addonName + ' account from node', {
                url: self.urls().deauthorize,
                textStatus: textStatus,
                error: error
            });
        });
        return request;
    },
    deauthorize: function() {
        /** Pop up a confirmation to deauthorize addon from this node.
         *  Send DELETE request if confirmed.
         */
        var self = this;
        bootbox.confirm({
            title: 'Deauthorize ' + self.addonName + '?',
            message: self.messages.CONFIRM_DEAUTH(),
            callback: function(confirmed) {
                if (confirmed) {
                    self._deauthorizeConfirm();
                }
            }
        });
    },
    /**
     * Must be used to update radio buttons and knockout view model simultaneously
     */
    cancelSelection: function() {
        this.selected(null);
    },
    togglePicker: function() {
        /**
         *  Toggles the visibility of the folder picker.
         */
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
    },
    treebeardOptions: function(){
        return {
            lazyLoadPreprocess: function(data) { 
                return data;
            },
            onPickFolder: function() {
                throw new Error('Subclassess of FolderPickerViewModel must implement an \'onPickFolder(evt, item)\' method');
            },
            resolveLazyloadUrl: function(item) {
                throw new Error('Subclassess of FolderPickerViewModel must implement an \'resolveLazyLoadUrl(item)\' method');
            }
        };
    },
    activatePicker: function() {
        /**
         *  Activates the HGrid folder picker.
         */
        var self = this;
        var opts = $.extend({}, {
            initialFolderPath: self.folder().path || '',
            // Fetch folders with AJAX
            filesData: self.urls().folders, // URL for fetching folders
            // Lazy-load each folder's contents
            // Each row stores its url for fetching the folders it contains
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
        }, self.treebeardOptions());
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            // Show loading indicator
            self.loading(true);
            $(self.folderPicker).folderpicker(opts);
        }
    }    
});

module.exports = FolderPickerViewModel;
