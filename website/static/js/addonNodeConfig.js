/**
 * Module that controls the addon node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var Raven = require('raven-js');

var ZeroClipboard = require('zeroclipboard');
ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var FolderPickerViewModel = require('js/folderPickerNodeConfig');

ko.punches.enableAll();

var AddonFolderPickerViewModel = oop.extend(FolderPickerViewModel, {
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
        self.messages.SUBMIT_SETTINGS_SUCCESS =  ko.pureComputed(function() {
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
        this.canShare(settings.canShare || false);
    },
    fetchAccounts: function() {
        var self = this;
        var request = $.get(self.urls().accounts);
        request.then(function(data) {
            return data.accounts;
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
    updateAccounts: function() {
        var self = this;
        return self.fetchAccounts()
        .done(function(accounts) {
            self.accounts(accounts.map(function(account) {
                return {
                    name: account.display_name,
                    id: account.id
                };
            }));
        });
    },       
    /**
     * Allows a user to create an access token from the nodeSettings page
     */
    connectAccount: function() {
        window.location.href = this.urls().auth;
    }
});

// Public API
function AddonNodeConfig(addonName, selector, url, folderPicker, opts) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    if (typeof opts === 'undefined') {
        opts = {};
    }
    self.viewModel = new AddonFolderPickerViewModel(addonName, url, selector, folderPicker, opts);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    AddonNodeConfig: AddonNodeConfig,
    _AddonNodeConfigViewModel: AddonFolderPickerViewModel
};
