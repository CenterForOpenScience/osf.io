'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var $modal = $('#boaCredentialsModal');
var oop = require('js/oop');
var osfHelpers = require('js/osfHelpers');
var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;
var language = require('js/osfLanguage').Addons.boa;

var ViewModel = oop.extend(OauthAddonFolderPicker,{
    constructor: function(addonName, url, selector, folderPicker, opts, tbOpts) {
        var self = this;
        // TODO: [OSF-7069]
        self.super.super.constructor.call(self, addonName, url, selector, folderPicker, tbOpts);
        self.super.construct.call(self, addonName, url, selector, folderPicker, opts, tbOpts);

        // Non-Oauth fields:
        self.username = ko.observable('');
        self.password = ko.observable('');

        self.credentialsChanged = ko.pureComputed(function() {
            return self.nodeHasAuth() && !self.validCredentials();
        });
    },
    clearModal : function() {
        var self = this;
    },
    connectAccount : function() {
        var self = this;

        if ( !self.username() && !self.password() ){
            self.changeMessage('Please enter a username and password.', 'text-danger');
            return;
        }

        var url = self.urls().auth;
        osfHelpers.postJSON(
            url,
            ko.toJS({
                password: self.password,
                username: self.username
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
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
        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with boa', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    },
   formatExternalName: function(item) {
        return {
            text: $osf.htmlEscape(item.name) + ' - ' + $osf.htmlEscape(item.profile),
            value: item.id
        };
    }
});

function BoaNodeConfig(selector, url) {
    var self = this;
    self.viewModel = new ViewModel('boa', url, selector, '#boaGrid', {});
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = BoaNodeConfig;
