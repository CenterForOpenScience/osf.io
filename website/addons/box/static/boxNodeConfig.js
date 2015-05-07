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

var AddonNodeConfigViewModel = require('js/addonNodeConfig')._AddonNodeConfigViewModel;
var $osf = require('js/osfHelpers');
var oop = require('js/oop');

ko.punches.enableAll();

var BoxNodeConfigViewModel = oop.extend(AddonNodeConfigViewModel, {
    constructor: function(addonName, url, selector, folderPicker) {
        var self = this;
        self.super.super.constructor.call(self, addonName, url, selector, folderPicker);
        self.userAccountId = ko.observable('');
        //externalAccounts
        self.accounts = ko.observable([]);

        self.messages.submitSettingsSuccess = ko.pureComputed(function() {
            return 'Successfully linked "' + $osf.htmlEscape(self.folder().name) + '". Go to the <a href="' +
                self.urls().files + '">Overview page</a> to view your citations.';
        });

        self.treebeardOptions = $.extend(
            {},
            AddonNodeConfigViewModel.prototype.treebeardOptions,
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
                resolveLazyloadUrl: function(item) {
                    return item.data.urls.folders;
                }.bind(this)
            });

        // Initial fetch from server
        self.fetchFromServer();
    },
    connectAccount: function() {
        var self = this;

        window.oauthComplete = function(res) {
            // Update view model based on response
            self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
            self.importAuth.call(self);
        };
        window.open(self.urls().auth);
    },  
});

function BoxNodeConfig(addonName, selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new BoxNodeConfigViewModel(addonName, url, selector, folderPicker);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    BoxNodeConfig: BoxNodeConfig,
    _BoxNodeConfigViewModel: BoxNodeConfigViewModel
};
