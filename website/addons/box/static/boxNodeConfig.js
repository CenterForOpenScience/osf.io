/**
* Module that controls the Box node settings. Includes Knockout view-model
* for syncing data, and HGrid-folderpicker for selecting a folder.
*/
'use strict';

var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var FolderPickerViewModel = require('js/folderPickerNodeConfig');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');

ko.punches.enableAll();
/**
 *  Knockout view model for the Box node settings widget.
 */
var ViewModel = oop.extend(FolderPickerViewModel, {
    constructor: function(addonName, url, selector, folderPicker) {
        var self = this;
        self.super.constructor.call(self, addonName, url, selector, folderPicker);
        self.userAccountId = ko.observable('');
        //externalAccounts
        self.accounts = ko.observable([]);

        self.messages.submitSettingsSuccess = ko.pureComputed(function() {
            return 'Successfully linked "' + $osf.htmlEscape(self.folder().name) + '". Go to the <a href="' +
                self.urls().files + '">Overview page</a> to view your citations.';
        });

        self.treebeardOptions = $.extend(
            {},
            FolderPickerViewModel.prototype.treebeardOptions,
            {
                /** Callback for chooseFolder action.
                *   Just changes the ViewModel's self.selected observable to the selected
                *   folder.
                */
                onPickFolder: function(evt, item) {
                    evt.preventDefault();
                    var name = item.data.path === 'All Files' ? '/ (Full Box)' : item.data.path.replace('All Files', '');
                    self.selected({name: name, path: item.data.path, id: item.data.id});
                    return false; // Prevent event propagation
                }.bind(this),
                lazyLoadPreprocess: function(data) {
                    return data.contents.filter(function(item) {
                    return item.kind === 'folder';
                    });
                },
                resolveLazyloadUrl: function(item) {
                    return this.urls().folders + item.data.id + '/?view=folders';
                }.bind(this)
            });

        // Initial fetch from server
        self.fetchFromServer();
    },
    fetchAccounts: function() {
        var self = this;
        var ret = $.Deferred();
        var request = $.get(self.urls().accounts);
        request.then(function(data) {
            ret.resolve(data.accounts);
        });
        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.updateAccountsError(), 'text-warning');
            Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
            ret.reject(xhr, textStatus, error);
        });
        return ret.promise();
    },
    updateAccounts: function() {
        var self = this;
        return self.fetchAccounts()
            .done(function(accounts) {
                self.accounts(
                    $.map(accounts, function(account) {
                        return {
                            name: account.display_name,
                            id: account.id
                        };
                    })
                );
            });
    },
    /**
     * Allows a user to create an access token from the nodeSettings page
     */
    connectAccount: function() {
        var self = this;

        window.oauthComplete = function(res) {
            // Update view model based on response
            self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
            self.importAuth.call(self);
        };
        window.open(self.urls().auth);
    },
    connectExistingAccount: function(account_id) {
        var self = this;

        return $osf.putJSON(
            self.urls().importAuth, {
                external_account_id: account_id
            }
        ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
    },
    _updateCustomFields: function(settings) {
        this.userAccountId(settings.userAccountId);
    },
    _serializeSettings: function(){
        return {
            external_account_id: this.userAccountId(),
            external_list_id: this.selected().id,
            external_list_name: this.selected().name
        };
    },
    importAuth: function() {
        var self = this;
        self.updateAccounts()
            .then(function(){
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
// Public API
function BoxNodeConfig(addonName, selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new ViewModel(addonName, url, selector, folderPicker);
    self.viewModel.updateFromData()
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    BoxNodeConfig: BoxNodeConfig,
    _BoxNodeConfigViewModel: ViewModel
};