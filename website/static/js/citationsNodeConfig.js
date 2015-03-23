/**
 * Module that controls the citations addons node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var FolderPickerViewModel = require('js/folderPickerNodeConfig');

ko.punches.enableAll();
/**
 * Knockout view model for citations node settings widget.
 */
var CitationsFolderPickerViewModel = oop.extend(FolderPickerViewModel, {
    constructor: function(addonName, url, selector, folderPicker) {
        var self = this;
        self.super.constructor.call(self, addonName, url, selector, folderPicker);
        self.userAccountId = ko.observable('');
    },
    updateAccounts: function() {
        var self = this;
        var request = $.get(self.urls().accounts);
        request.done(function(data) {
            self.accounts(data.accounts.map(function(account) {
                return {
                    name: account.display_name,
                    id: account.id
                };
            }));
        });
        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.UPDATE_ACCOUNTS_ERROR(), 'text-warning');
            Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
        });
        return request;
    },
    /**
     * Allows a user to create an access token from the nodeSettings page
     */
    connectAccount: function() {
        var self = this;

        window.oauthComplete = function(res) {
            // Update view model based on response
            self.changeMessage(self.messages.CONNECT_ACCOUNT_SUCCESS(), 'text-success', 3000);
            self.updateAccounts()
                .done(function() {
                    $osf.postJSON(
                        self.urls().importAuth, {
                            external_account_id: self.accounts()[0].id
                        }
                    ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
                });
        };
        window.open(self.urls().auth);
    },
    connectExistingAccount: function(account_id) {
        var self = this;

        return $osf.postJSON(
            self.urls().importAuth, {
                external_account_id: account_id
            }
        ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
    },
    _updateCustomFields: function(settings){
        this.userAccountId(settings.userAccountId);
    },
    _serializeSettings: function(){
        return {
            external_account_id: this.userAccountId(),
            external_list_id: this.selected().id,
            external_list_name: this.selected().name
        };
    },
    treebeardOptions: $.extend(
        {}, 
        FolderPickerViewModel.prototype.treebeardOptions,
        {
            /** Callback for chooseFolder action.
             *   Just changes the ViewModel's self.selected observable to the selected
             *   folder.
             */
            onPickFolder: function(evt, item){
                evt.preventDefault();
                this.selected({
                    name: item.data.name,
                    id: item.data.id
                });
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
        }
    )
});

// Public API
function CitationsNodeConfig(addonName, selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new CitationsFolderPickerViewModel(addonName, url, selector, folderPicker);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    CitationsNodeConfig: CitationsNodeConfig,
    _CitationsNodeConfigViewModel: CitationsFolderPickerViewModel
};
