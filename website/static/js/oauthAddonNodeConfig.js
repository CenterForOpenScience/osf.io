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


var ZeroClipboard = require('zeroclipboard');
ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
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
        // whether the auth token is valid
        self.validCredentials = ko.observable(true);
        // Emails of contributors, can only be populated by activating the share dialog
        self.emails = ko.observableArray([]);
        self.loading = ko.observable(false);
        // Whether the contributor emails have been loaded from the server
        self.loadedEmails = ko.observable(false);
        // externalAccounts
        self.accounts = ko.observable([]);
        // List of contributor emails as a comma-separated values
        self.emailList = ko.pureComputed(function() {
            return self.emails().join([', ']);
        });
        self.selectedFolderType = ko.pureComputed(function() {
            var userHasAuth = self.userHasAuth();
            var selected = self.selected();
            return (userHasAuth && selected) ? selected.type : '';
        });
        self.messages.submitSettingsSuccess =  ko.pureComputed(function() {
            return 'Successfully linked "' + $osf.htmlEscape(self.folder().name) + '". Go to the <a href="' +
                self.urls().files + '">Files page</a> to view your content.';
        });
        // Overrides
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
                    self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
                    self.updateAccounts(function() {
                        $osf.putJSON(
                            self.urls().importAuth, {
                                external_account_id: self.accounts()[0].id
                            }
                        ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
                    });
                };
                window.open(self.urls().auth);
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
                    return item.data.urls.folders;
                }
            }
        );
    },
    toggleShare: function() {
        if (this.currentDisplay() === this.SHARE) {
            this.currentDisplay(null);
        } else {
            // Clear selection
            this.cancelSelection();
            this.currentDisplay(this.SHARE);
            this.activateShare();
        }
    },
    fetchEmailList: function(){
        var self = this;

        var ret = $.Deferred();
        var promise = ret.promise();
        if(!self.loadedEmails()){
            $.ajax({
                url: self.urls().emails,
                type: 'GET',
                dataType: 'json'
            }).done(function(res){
                self.loadedEmails(true);
                ret.resolve(res.results.emails);
            }).fail(function(xhr, status, error){
                Raven.captureMessage('Could not GET ' + self.addonName + ' email list', {
                    url: self.urls().emails,
                    textStatus: status,
                    error: error
                });
                ret.reject(xhr, status, error);
            });
        }
        else{
            ret.resolve(self.emails());
        }
        return promise;
    },
    activateShare: function() {
        var self = this;
        self.fetchEmailList()
            .done(function(emails){
                self.emails(emails);
            });
        var $copyBtn = $(self.selector).find('.copyBtn');
        new ZeroClipboard($copyBtn);
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
    importAuth: function(){
        var self = this;

        self.updateAccounts(function() {
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose ' + self.addonName + ' Access Token to Import',
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
                    title: 'Import ' + self.addonName + ' Access Token?',
                    message: self.messages.confirmAuth(),
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    }
                });
            }
        });
    }
});

OauthAddonFolderPickerViewModel.prototype.connectExistingAccount = function(account_id) {
     var self = this;

    $osf.putJSON(
        self.urls().importAuth, {
            external_account_id: account_id
        }
    ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
};

OauthAddonFolderPickerViewModel.prototype.updateAccounts = function(callback) {
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
        Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
    });
};

// Public API
function OauthAddonNodeConfig(addonName, selector, url, folderPicker, opts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    if (typeof opts === 'undefined') {
        opts = {};
    }
    self.viewModel = new OauthAddonFolderPickerViewModel(addonName, url, selector, folderPicker, opts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    OauthAddonNodeConfig: OauthAddonNodeConfig,
    _OauthAddonNodeConfigViewModel: OauthAddonFolderPickerViewModel
};