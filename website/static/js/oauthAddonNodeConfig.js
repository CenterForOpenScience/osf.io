/**
 * Module that controls the addon node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var FolderPickerViewModel = require('js/folderPickerNodeConfig');

ko.punches.enableAll();

/**
 * View model to support instances of AddonNodeConfig (folder picker widget)
 *
 * @class AddonFolderPickerViewModel
 * @param {String} addonName Full display name of the addon
 * @param {String} url API url to initially fetch settings
 * @param {String} selector CSS selector for containing div
 * @param {String} folderPicker CSS selector for folderPicker div
 * @param {Object} opts Optional overrides to the class' default treebeardOptions, in particular onPickFolder
 */
var OauthAddonFolderPickerViewModel = oop.extend(FolderPickerViewModel, {
    constructor: function(addonName, url, selector, folderPicker, opts) {
        var self = this;
        self.super.constructor.call(self, addonName, url, selector, folderPicker);
        // externalAccounts
        self.accounts = ko.observableArray();
        self.selectedFolderType = ko.pureComputed(function() {
            var userHasAuth = self.userHasAuth();
            var selected = self.selected();
            return (userHasAuth && selected) ? selected.type : '';
        });
        self.messages.submitSettingsSuccess =  ko.pureComputed(function() {
            return 'Successfully linked "' + $osf.htmlEscape(self.options.decodeFolder(self.folder().name)) + '". Go to the <a href="' +
                self.urls().files + '">Files page</a> to view your content.';
        });
        var defaults = {
            onPickFolder: function(evt, item) {
                evt.preventDefault();
                var name = item.data.path !== '/' ? item.data.path : '/ (Full ' + self.addonName + ')';
                self.selected({
                    name: name,
                    path: item.data.path,
                    id: item.data.id
                });
                return false; // Prevent event propagation
            },
            /**
             * Allows a user to create an access token from the nodeSettings page
             */
            connectAccount: function() {
                var self = this;

                window.oauthComplete = function(res) {
                    // Update view model based on response
                    self.updateAccounts().then(function() {
                        try{
                            $osf.putJSON(
                                self.urls().importAuth, {
                                    external_account_id: self.accounts()[0].id
                                }
                            ).done(self.onImportSuccess.bind(self)
                            ).fail(self.onImportError.bind(self));

                            self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
                        }
                        catch(err){
                            self.changeMessage(self.messages.connectAccountDenied(), 'text-danger', 6000);
                        }
                    });
                };
                window.open(self.urls().auth);
            },
            decodeFolder: function(folder_name) {
                return folder_name;
            }
        };
        // Overrides
        self.options = $.extend({}, defaults, opts);
        // Treebeard config
        self.treebeardOptions = $.extend(
            {},
            FolderPickerViewModel.prototype.treebeardOptions,
            {
                onPickFolder: function(evt, item) {
                    return this.options.onPickFolder.call(this, evt, item);
                }.bind(this),
                resolveLazyloadUrl: function(item) {
                    if (item.data.links) {
                        return item.data.links.children;
                    }
                    return item.data.urls.folders;
                }
            }
        );
    },
    afterUpdate: function() {
        var self = this;
        if (self.nodeHasAuth() && !self.validCredentials()) {
            var message;
            if (self.userIsOwner()) {
                message = self.messages.invalidCredOwner();
            }
            else {
                message = self.messages.invalidCredNotOwner();
            }
            self.changeMessage(message, 'text-danger');
        }
    },
    _updateCustomFields: function(settings){
        this.validCredentials(settings.validCredentials);
    },
     /**
     * Allows a user to create an access token from the nodeSettings page
     */
    connectAccount: function() {
        this.options.connectAccount.call(this);
    },
    /**
    * Imports addon settings from user's account. If multiple addon accounts are connected, allow user to pick between them.
    */
    importAuth: function(){
        var self = this;

        self.updateAccounts().then(function () {
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose ' + self.addonName + ' Account to Import',
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
                    callback: (self.connectExistingAccount.bind(self)),
                    buttons: {
                        confirm:{
                            label:'Import',
                        }
                    }
                });
            } else {
                bootbox.confirm({
                    title: 'Import ' + self.addonName + ' Account?',
                    message: self.messages.confirmAuth(),
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    },
                    buttons: {
                        confirm: {
                            label:'Import',
                        }
                    }
                });
            }
        });
    },
    /**
    * Associates selected external account with this node, or handles error.
    */
    connectExistingAccount: function(account_id) {
        var self = this;
        if (account_id !== null) {
            return $osf.putJSON(
                self.urls().importAuth, {
                    external_account_id: account_id
                }
            ).done(self.onImportSuccess.bind(self)
            ).fail(self.onImportError.bind(self));
        }
        return;
    },
    updateAccounts: function() {
        var self = this;
        var request = $.get(self.urls().accounts);
        return request.done(function(data) {
            self.accounts(data.accounts.map(function(account) {
                return {
                    name: account.display_name,
                    id: account.id
                };
            }));
        }).fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.UPDATE_ACCOUNTS_ERROR(), 'text-warning');
            Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
                extra: {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    },
});

// Public API
function OauthAddonNodeConfig(addonName, selector, url, folderPicker, opts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    opts = opts || {};
    self.viewModel = new OauthAddonFolderPickerViewModel(addonName, url, selector, folderPicker, opts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    OauthAddonNodeConfig: OauthAddonNodeConfig,
    _OauthAddonNodeConfigViewModel: OauthAddonFolderPickerViewModel
};
