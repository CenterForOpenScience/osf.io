'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var OAuthAddonSettingsViewModel = require('js/addonSettings.js').OAuthAddonSettingsViewModel;
var language = require('js/osfLanguage').Addons.boa;
var osfHelpers = require('js/osfHelpers');
var oop = require('js/oop');
var $modal = $('#boaCredentialsModal');

var ViewModel = oop.extend(OAuthAddonSettingsViewModel,{
    constructor: function(url){
        var self = this;
        self.super.constructor.call(self, 'boa', 'Boa');

        self.url = url;

        self.username = ko.observable();
        self.password = ko.observable();
        self.loaded = ko.observable(false);
    },
    fetch: function(){
        var self = this;
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            self.loaded(true);
            self.updateAccounts();
        }).fail(function (xhr, textStatus, error) {
            self.setMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET Boa settings', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
        });
    },
    clearModal: function() {
        var self = this;
    },
    connectAccount: function() {
        var self = this;
        if ( !(self.username() && self.password()) ){
            self.setMessage('Please enter a username and password.', 'text-danger');
            return;
        }

        osfHelpers.postJSON(
            self.url,
            ko.toJS({
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
            Raven.captureMessage('Could not authenticate with Boa', {
                textStatus: textStatus,
                error: error,
            });
        });
    },
});

function BoaUserConfig(selector, url) {
    var self = this;
    self.selector = selector;
    self.url = url;
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    BoaViewModel: ViewModel,
    BoaUserConfig: BoaUserConfig
};
