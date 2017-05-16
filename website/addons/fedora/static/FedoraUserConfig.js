'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var OAuthAddonSettingsViewModel = require('js/addonSettings.js').OAuthAddonSettingsViewModel;
var language = require('js/osfLanguage').Addons.fedora;
var osfHelpers = require('js/osfHelpers');
var oop = require('js/oop');
var $modal = $('#fedoraCredentialsModal');

var FedoraViewModel = oop.extend(OAuthAddonSettingsViewModel,{
    constructor: function(url){
        var self = this;
        self.super.constructor.call(self, 'fedora', 'Fedora');

        const otherString = 'Other (Please Specify)';

        self.url = url;
        self.username = ko.observable();
        self.password = ko.observable();
        self.hosts = ko.observableArray([]);
        self.selectedHost = ko.observable();
        self.customHost = ko.observable();
        self.loaded = ko.observable(false);

        self.host = ko.pureComputed(function() {
            return self.useCustomHost() ? self.customHost() : self.selectedHost();
        });
        self.visibleHosts = ko.pureComputed(function() {
            return self.hosts().concat([otherString]);
        });
        self.useCustomHost = ko.pureComputed(function() {
            return (self.selectedHost() === otherString || !self.hasDefaultHosts());
        });
        self.showCredentialInput = ko.pureComputed(function() {
            return true;
        });
        self.hasDefaultHosts = ko.pureComputed(function() {
            return Boolean(self.hosts().length);
        });
    },
    updateAccounts: function(){
	var self = this;
	self.super.updateAccounts.call(self);
    },
    fetch :function(){
        var self = this;
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            self.hosts(response.hosts);
            self.loaded(true);
            self.updateAccounts();
        }).fail(function (xhr, textStatus, error) {
            self.setMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET fedora settings', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
        });
    },
    clearModal : function() {
        var self = this;
        self.selectedHost(null);
        self.customHost(null);
    },
    connectAccount : function() {
        var self = this;
        // Selection should not be empty
        if( self.hasDefaultHosts() && !self.selectedHost() ){
            if (self.useCustomHost()){
                self.setMessage('Please enter an fedora server.', 'text-danger');
            } else {
                self.setMessage('Please select an fedora server.', 'text-danger');            
            }
            return;
        }
        if ( !self.useCustomHost() && !self.username() && !self.password() ){
            self.setMessage('Please enter a username and password.', 'text-danger');
            return;
        }
        if ( self.useCustomHost() && ( !self.customHost() || !self.username() || !self.password() ) )  {
            self.setMessage('Please enter an fedora host and credentials.', 'text-danger');
            return;
        }
        return osfHelpers.postJSON(
            self.url,
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
            Raven.captureMessage('Could not authenticate with fedora', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
        });
    },
});

function FedoraUserConfig(selector, url) {
    var self = this;
    self.selector = selector;
    self.url = url;
    self.viewModel = new FedoraViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    FedoraViewModel: FedoraViewModel,
    FedoraUserConfig: FedoraUserConfig
};
