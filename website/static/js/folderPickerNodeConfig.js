/**
 * Abstract module that controls the addon node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';
require('css/addon_folderpicker.css');
var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var m = require('mithril');


var FolderPicker = require('js/folderpicker');
var ZeroClipboard = require('zeroclipboard');
ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
var $osf = require('js/osfHelpers');

var oop = require('js/oop');


/**
 * @class FolderPickerViewModel
 * @param {String} addonName Full display name of the addon
 * @param {String} url API url to initially fetch settings
 * @param {String} selector CSS selector for containing div
 * @param {String} folderPicker CSS selector for folderPicker div
 *
 * Notes:
 * - Subclasses of this VM can be created using the oop module like: oop.extend(FolderPickerViewModel, { ... });
 * - Subclasses must:
 *   - provide a VM.messages.submitSettingsSuccess()
 *   - override VM.treebeardOptions.onPickFolder and VM.treebeardOptions.resolveLazyloadUrl
 * - Subclasses can:
 *   - implement an _updateCustomFields method to capture additional parameters in updateFromData
 */
var FolderPickerViewModel = oop.defclass({
    constructor: function(addonName, url, selector, folderpickerSelector) {
        var self = this;
        self.url = url;
        self.addonName = addonName;
        self.selector = selector;
        self.folderpickerSelector = folderpickerSelector;
        self.folderpicker = null;
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
        // whether import token has been clicked
        self.loadingImport = ko.observable(false);
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

        var addonSafeName = $osf.htmlEscape(self.addonName);
        self.messages = {
            invalidCredOwner: ko.pureComputed(function() {
                return 'Could not retrieve ' + addonSafeName + ' settings at ' +
                    'this time. The credentials associated with this ' + addonSafeName + ' account may no longer be valid.' +
                    ' Try disconnecting and reconnecting the ' + addonSafeName + ' account on your <a href="' +
                    self.urls().settings + '">account settings page</a>.';
            }),
            invalidCredNotOwner: ko.pureComputed(function() {
                return 'Could not retrieve ' + addonSafeName + ' settings at ' +
                    'this time. The ' + addonSafeName + ' addon credentials may no longer be valid.' +
                    ' Contact ' + $osf.htmlEscape(self.ownerName()) + ' to verify.';
            }),
            cantRetrieveSettings: ko.pureComputed(function() {
                return 'Could not retrieve ' + addonSafeName + ' settings at ' +
                    'this time. Please refresh ' +
                    'the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
            }),
            updateAccountsError: ko.pureComputed(function() {
                return 'Could not retrieve ' + addonSafeName + ' account list at ' +
                    'this time. Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
            }),
            deauthorizeSuccess: ko.pureComputed(function() {
                return 'Disconnected ' + addonSafeName + '.';
            }),
            deauthorizeFail: ko.pureComputed(function() {
                return 'Could not disconnect ' + addonSafeName + ' account because of an error. Please try again later.';
            }),
            connectAccountSuccess: ko.pureComputed(function() {
                return 'Successfully connected a ' + addonSafeName + ' account';
            }),
            connectAccountDenied: ko.pureComputed(function() {
                return 'Error while authorizing addon. Please log in to your ' + addonSafeName + ' account and grant access to the OSF to enable this addon.';
            }),
            submitSettingsSuccess: ko.pureComputed(function() {
                throw new Error('Subclasses of FolderPickerViewModel must provide a message for successful settings updates. ' +
                                'This should take the form: "Successfully linked \'{FOLDER_NAME}\'. Go to the <a href="{URL}"> ' +
                                '{PAGE_NAME} to view your {CONTENT_TYPE}.');
            }),
            submitSettingsError: ko.pureComputed(function() {
                return 'Could not change ' + addonSafeName + ' settings. Please try again later.';
            }),
            confirmDeauth: ko.pureComputed(function() {
                return 'Are you sure you want to remove this ' + addonSafeName + ' account?';
            }),
            confirmAuth: ko.pureComputed(function() {
                return 'Are you sure you want to link your ' + addonSafeName + ' account with this project?';
            }),
            tokenImportSuccess: ko.pureComputed(function() {
                return 'Successfully imported ' + addonSafeName + ' account from profile.';
            }),
            tokenImportError: ko.pureComputed(function() {
                return 'Error occurred while importing ' + addonSafeName + ' account.';
            }),
            connectError: ko.pureComputed(function() {
                return 'Could not connect to ' + addonSafeName + ' at this time. Please try again later.';
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
            var onclick = self.loadingImport();
            return userHasAuth && !nodeHasAuth && loaded && !onclick;
        });

        /** Whether or not show loading icon after import button */
        self.showLoading = ko.pureComputed(function() {
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            var onclick = self.loadingImport();
            return userHasAuth && !nodeHasAuth && loaded && onclick;
        });

        /** Whether or not to show the full settings pane. */
        self.showSettings = ko.pureComputed(function() {
            return self.nodeHasAuth() && self.validCredentials();
        });

        /** Whether or not to show the Connect Account button */
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
            return (nodeHasAuth && folder && folder.name) ? decodeURIComponent(folder.name.trim()) : '';
        });

        self.selectedFolderName = ko.pureComputed(function() {
            var userIsOwner = self.userIsOwner();
            var selected = self.selected();
            var name = selected.name ? decodeURIComponent(selected.name) : 'None';
            name = name.replace('All Files', 'Full ' + addonName);
            return userIsOwner ? name : '';
        });

        self.treebeardOptions = {
            lazyLoadPreprocess: function(data) {
                return data;
            },
            onPickFolder: function() {
                throw new Error('Subclasses of FolderPickerViewModel must implement a "onPickFolder(evt, item)" method');
            },
            resolveLazyloadUrl: function(item) {
                throw new Error('Subclasses of FolderPickerViewModel must implement a "resolveLazyloadUrl(item)" method');
            }
        };
    },
    /**
     * Change the flashed message.
     *
     * @param {String} text Text to show
     * @param {String} css CSS class of text to be show, defaults to 'text-info'
     * @param {Number} timeout Optional number of ms to wait until removing the flashed message
     */
    changeMessage: function(text, css, timeout) {
        var self = this;

        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.resetMessage();
            }, timeout);
        }
    },
    resetMessage: function() {
        this.message('');
        this.messageClass('text-info');
    },
    /**
     * Abstract hook called after updateFromData, before the promise is resolved.
     * - use to validate the VM state after update
     **/
    afterUpdate: function() {},
    /**
     * Abstract hook where subclasses can capture extra data from the API response
     *
     * @param {Object} settings Settings passed from server response in #updateFromData
     */
    _updateCustomFields: function(settings) {},
    /**
     * Update the view model from data returned from the server or data passed explicitly.
     *
     * @param {Object} data optional data to update from rather than from API
     */
    updateFromData: function(data) {
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
            self.afterUpdate();
            ret.resolve();
        };
        if (typeof data === 'undefined'){
            self.fetchFromServer()
                .done(applySettings)
                .fail(ret.reject);
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
            self.loadedSettings(true);
            ret.resolve(response.result);
        });
        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.cantRetrieveSettings(), 'text-danger');
            Raven.captureMessage('Could not GET ' + self.addonName + 'settings', {
                extra: {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                }
            });
            ret.reject(xhr, textStatus, error);
        });
        return ret.promise();
    },
    _serializeSettings: function(){
        return ko.toJS(this);
    },
    /**
     * Send a PUT request to change the linked folder.
     */
    submitSettings: function() {
        var self = this;
        function onSubmitSuccess(response) {
            // Update folder in ViewModel
            self.folder(response.result.folder);
            self.urls(response.result.urls);
            self.cancelSelection();
            self.changeMessage(self.messages.submitSettingsSuccess(), 'text-success');
        }
        function onSubmitError(xhr, status, error) {
            self.changeMessage(self.messages.submitSettingsError(), 'text-danger');
            Raven.captureMessage('Failed to update ' + self.addonName + ' settings.', {
                extra: {
                    xhr: xhr,
                    status: status,
                    error: error
                }
            });
        }
        return $osf.putJSON(self.urls().config, self._serializeSettings())
            .done(onSubmitSuccess)
            .fail(onSubmitError);
    },
    onImportSuccess: function(response) {
        var self = this;       
        var msg = response.message || self.messages.tokenImportSuccess();
        // Update view model based on response
        self.changeMessage(msg, 'text-success', 3000);
        self.updateFromData(response.result);
        self.loadedFolders(false);
        self.activatePicker();
    },
    onImportError: function(xhr, status, error) {
        var self = this;
        self.changeMessage(self.messages.tokenImportError(), 'text-danger');
        Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
            extra: {
                xhr: xhr,
                status: status,
                error: error
            }
        });
    },
    _importAuthPayload: function() {
        return {};
    },
    _importAuthConfirm: function() {
        var self = this;
        return $osf.putJSON(self.urls().importAuth, self._importAuthPayload())
            .done(self.onImportSuccess.bind(self))
            .fail(self.onImportError.bind(self));
    },
    /**
     * Send PUT request to import access token from user profile.
     */
    importAuth: function() {
        var self = this;
        bootbox.confirm({
            title: 'Import ' + $osf.htmlEscape(self.addonName) + ' Account?',
            message: self.messages.confirmAuth(),
            callback: function(confirmed) {
                if (confirmed) {
                    self._importAuthConfirm();
                    self.loadingImport(true);
                }
            },
            buttons:{
                confirm:{
                    label:'Import'
                }
            }
        });
    },
    /**
     * Send DELETE request to deauthorize this node.
     */
    _deauthorizeConfirm: function(){
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
            self.changeMessage(self.messages.deauthorizeSuccess(), 'text-warning', 3000);
            self.loadedFolders(false);
            self.destroyPicker();
        });
        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.deauthorizeFail(), 'text-danger');
            Raven.captureMessage('Could not deauthorize ' + self.addonName + ' account from node', {
                extra: {
                    url: self.urls().deauthorize,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
        return request;
    },
    /** Pop up a confirmation to deauthorize addon from this node.
     *  Send DELETE request if confirmed.
     */
    deauthorize: function() {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect ' + $osf.htmlEscape(self.addonName) + ' Account?',
            message: self.messages.confirmDeauth(),
            callback: function(confirmed) {
                if (confirmed) {
                    self._deauthorizeConfirm();
                    self.loadingImport(false);
                }
            },
            buttons:{
                confirm:{
                    label:'Disconnect',
                    className:'btn-danger'
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
    /**
     *  Toggles the visibility of the folder picker.
     */
    togglePicker: function() {
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
    destroyPicker: function() {
        if (this.folderpicker) {
            this.folderpicker.destroy();
        }
    },
    doActivatePicker: function(opts) {
        var self = this;
        // Show loading indicator
        self.loading(true);
        self.folderpicker = new FolderPicker(self.folderpickerSelector, opts);
    },
    /**
     *  Activates the HGrid folder picker.
     */
    activatePicker: function() {
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
            multiselect: false,
            allowMove: false,
            ajaxOptions: {
                error: function(xhr, textStatus, error) {
                    self.loading(false);
                    self.changeMessage(self.messages.connectError(), 'text-danger');
                    Raven.captureMessage('Could not GET get ' + self.addonName + ' contents.', {
                        extra: {
                            textStatus: textStatus,
                            error: error
                        }
                    });
                }
            },
            folderPickerOnload: function() {
                // Hide loading indicator
                self.loading(false);
                // Set flag to prevent repeated requests
                self.loadedFolders(true);
            },
            resolveRows: function(item) {
                item.css = '';
                return [
                {
                    data : 'name',  // Data field name
                    folderIcons : true,
                    filter : false,
                    custom : function(item, col) {
                        //This is bad, but probably necessary. GoogleDrive returns URI encoded folder names, but (most/all?) others don't
                        return m('span', decodeURIComponent(item.data.name));
                    }
                },
                {
                    css : 'p-l-xs',
                    sortInclude : false,
                    custom : FolderPicker.selectView
                }
            ];
            },
            xhrconfig: $osf.setXHRAuthorization,
            lazyLoadPreprocess: function(data) {
                // Also handle data from API -- squash `attributes` to what TB expects
                // TODO: [OSF-6384] DRY this up when PR #5240 goes in
                if (data.data) {
                    $.each(data.data, function(i, obj) {
                        var saved_attributes = obj.attributes;
                        delete obj.attributes;
                        $.extend(true, obj, saved_attributes);
                    });
                }
                return data;
            },
        }, self.treebeardOptions);
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            self.doActivatePicker(opts);
        }
    }
});

module.exports = FolderPickerViewModel;
