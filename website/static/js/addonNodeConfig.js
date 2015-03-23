/**
 * Module that controls the addon node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');

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
        // List of contributor emails as a comma-separated values
        self.emailList = ko.pureComputed(function() {
            return self.emails().join([', ']);
        });
        self.canShare = ko.observable(false);
        self.disableShare = ko.pureComputed(function() {
            var isRoot = self.folder().path === 'All Files';
            var notSet = (self.folder().path == null);
            return !(self.urls().emails) || !self.validCredentials() || isRoot || notSet;
        });
        self.selectedFolderType = ko.pureComputed(function() {
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
                    path: item.data.path,
                    id: item.data.id
                });
                return false; // Prevent event propagation
            }
        };
        // Overrides
        self.options = $.extend(self.options, opts);
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
    activateShare: function() {
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
    },
    _updateCustomFields: function(settings){
        this.validCredentials(settings.validCredentials);
        this.canShare(settings.canShare || false);
    },
    connectAccount: function() {
        /**
         * Allows a user to create an access token from the nodeSettings page
         */
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
    },
    treebeardOptions: function(){
        return $.extend(
            {}, 
            this.super.treebeardOptions(),
            {
                onPickFolder: function(evt, item) {
                    return this.options.onPickFolder.call(this, evt, item);
                }.bind(this),
                resolveLazyloadUrl: function(item) {
                    return item.data.urls.folders;
                }
            });
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
