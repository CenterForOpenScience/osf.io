'use strict';

var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var $modal = $('#ownCloudCredentialsModal');
var oop = require('js/oop');
var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;
var language = require('js/osfLanguage').Addons.owncloud;

var ViewModel = oop.extend(OauthAddonFolderPicker,{
    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        self.super.constructor(addonName, url, selector, folderPicker, tbOpts);
        // Non-Oauth fields:
        self.username = ko.observable("");
        self.password = ko.observable("");
        self.hosts = ko.observableArray([]);
        self.selectedHost = ko.observable();    // Host specified in select element
        self.customHost = ko.observable();      // Host specified in input element
        self.savedHost = ko.observable();       // Configured host

        const otherString = 'Other (Please Specify)';
        // Designated host, specified from select or input element
        self.host = ko.pureComputed(function() {
            return self.useCustomHost() ? self.customHost() : self.selectedHost();
        });
        // Hosts visible in select element. Includes presets and "Other" option
        self.visibleHosts = ko.pureComputed(function() {
            return self.hosts().concat([otherString]);
        });
        // Whether to use select element or input element for host designation
        self.useCustomHost = ko.pureComputed(function() {
            return self.selectedHost() === otherString;
        });
        self.credentialsChanged = ko.pureComputed(function() {
            return self.nodeHasAuth() && !self.validCredentials();
        });
        self.showCredentialInput = ko.pureComputed(function() {
            return (self.credentialsChanged() && self.userIsOwner()) ||
                (!self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings());
        });

        // Overrides
        var defaults = {
            onPickFolder: function(evt, item) {
                evt.preventDefault();
                var name = item.data.path !== '/' ? item.data.path : '/ (Full ' + self.addonName + ')';
                var folder = {
                    name: name,
                    path: item.data.path,
                    id: item.data.id
                };
                self.selected(folder);
                self.folder(folder);
                return false; // Prevent event propagation
            },
            connectAccount: function() {
                window.location.href = this.urls().auth;
            },
            decodeFolder: function(folder_name) {
                return folder_name;
            }
        };
        self.options = $.extend({}, defaults, opts);
        // Treebeard config
        self.treebeardOptions = $.extend(
            {},
            OauthAddonFolderPicker.prototype.treebeardOptions,
            {
                onPickFolder: function(evt, item) {
                    return this.options.onPickFolder.call(this, evt, item);
                }.bind(this),
                resolveLazyloadUrl: function(item) {
                    return item.data.urls.folders;
                },
                decodeFolder: function(item) {
                    return this.options.decodeFolder.call(this, item);
                }.bind(this)
            }
        );

    },
    clearModal : function() {
        var self = this;
        self.message('');
        self.messageClass('text-info');
        self.selectedHost(null);
        self.customHost(null);
    },
    connectAccount : function() {
        var self = this;
        // Selection should not be empty
        if( !self.selectedHost() ){
            self.setMessage("Please select a OwnCloud server.", 'text-danger');
            return;
        }

        if ( !self.useCustomHost() && !self.username() && !self.password() ){
            self.setMessage("Please enter a username and password.", 'text-danger');
            return;
        }

        if ( self.useCustomHost() && ( !self.customHost() || !self.username() || !self.password() ) )  {
            self.setMessage("Please enter a OwnCloud host and credentials.", 'text-danger');
            return;
        }

        var url = self.urls().create;

        return osfHelpers.postJSON(
            url,
            ko.toJS({
                host: self.host,
                password: self.password,
                username: self.username
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts();

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.setMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with OwnCloud', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    },
});

function OwnCloudNodeConfig(selector, url) {
    var self = this;
    self.viewModel = new ViewModel('owncloud', url, selector, '#owncloudGrid', {});
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = OwnCloudNodeConfig;
