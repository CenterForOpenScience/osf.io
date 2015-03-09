'use strict';

require('../../css/user-addon-settings.css');
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('osfHelpers');
var AddonPermissionsTable = require('addonPermissions');

ko.punches.enableAll();

// Set up submission for addon selection form
var checkedOnLoad = $('#selectAddonsForm input:checked');

// TODO: Refactor into a View Model
$('#selectAddonsForm').on('submit', function() {

    var formData = {};
    $('#selectAddonsForm').find('input').each(function(idx, elm) {
        var $elm = $(elm);
        formData[$elm.attr('name')] = $elm.is(':checked');
    });

    var unchecked = checkedOnLoad.filter($('#selectAddonsForm input:not(:checked)'));

    var submit = function() {
        var request = $osf.postJSON('/api/v1/settings/addons/', formData);
        request.done(function() {
            window.location.reload();
        });
        request.fail(function() {
            var msg = 'Sorry, we had trouble saving your settings. If this persists please contact <a href="mailto: support@osf.io">support@osf.io</a>';
            bootbox.alert({title: 'Request failed', message: msg});
        });
    };

    if(unchecked.length > 0) {
        var uncheckedText = $.map(unchecked, function(el){
            return ['<li>', $(el).closest('label').text().trim(), '</li>'].join('');
        }).join('');
        uncheckedText = ['<ul>', uncheckedText, '</ul>'].join('');
        bootbox.confirm({
            title: 'Are you sure you want to remove the add-ons you have deselected? ',
            message: uncheckedText,
            callback: function(result) {
                if (result) {
                    submit();
                } else{
                    unchecked.each(function(i, el){ $(el).prop('checked', true); });
                }
            }
        });
    }
    else {
        submit();
    }
    return false;
});

var addonEnabledSettings = window.contextVars.addonEnabledSettings;
for (var i=0; i < addonEnabledSettings.length; i++) {
       var addonName = addonEnabledSettings[i];
       if (typeof window.contextVars.addonsWithNodes !== 'undefined' && addonName in window.contextVars.addonsWithNodes) {
           AddonPermissionsTable.init(window.contextVars.addonsWithNodes[addonName].shortName,
                                      window.contextVars.addonsWithNodes[addonName].fullName);
   }
}

/***************
* OAuth addons *
****************/
var ConnectedProject = function(data) {
    var self = this;
    self.title = data.title;
    self.id = data.id;
    self.urls = data.urls;
};

var ExternalAccount = function(data) {
    var self = this;
    self.name = data.display_name;
    self.id = data.id;

    self.connectedNodes = ko.observableArray();

    ko.utils.arrayMap(data.nodes, function(item) {
        self.connectedNodes.push(new ConnectedProject(item));
    });

    self.deauthorizeNode = function(node) {
        console.log(node);
        var url = node.urls.deauthorize;
        $.ajax({
            url: url,
            type: 'DELETE'
        }).done(function(data) {
            self.connectedNodes.remove(node);
        }).fail(function(xhr, status, error) {
            Raven.captureMessage('Error deauthorizing node: ' + node.id, {
                url: url, status: status, error: error
            });
        });
    }

};

var OAuthAddonSettingsViewModel = function(name, displayName) {
    var self = this;
    self.name = name;
    self.properName = displayName;
    self.accounts = ko.observableArray();
    self.message = ko.observable('');
    self.messageClass = ko.observable('');

    self.setMessage = function(msg, cls) {
        self.message(msg);
        self.messageClass(cls || '');
    };

    self.connectAccount = function() {
        window.oauthComplete = function() {
            self.updateAccounts();
            self.setMessage('Add-on successfully authorized. To link this add-on to an OSF project, go to the settings page of the project, enable ' + self.properName + ', and choose content to connect.', '.text-success');
        };
        window.open('/oauth/connect/' + self.name + '/');
    };

    self.askDisconnect = function(account) {
        bootbox.confirm({
            title: 'Delete account?',
            message: '<p class="overflow">' +
                'Are you sure you want to delete account <strong>' +
                account.name + '</strong>?' +
                '</p>',
            callback: function(confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            }
        });
    };

    self.disconnectAccount = function(account) {
        var url = '/api/v1/oauth/accounts/' + account.id + '/';
        $.ajax({
            url: url,
            type: 'DELETE'
        }).done(function(data) {
            self.updateAccounts();
        }).fail(function(xhr, status, error) {
            Raven.captureMessage('Error while removing addon authorization for ' + account.id, {
                url: url, status: status, error: error
            });
        });
    };

    self.updateAccounts = function() {
        var url = '/api/v1/settings/' + self.name + '/accounts/';
        $.get(url).done(function(data) {
            self.accounts(data.accounts.map(function(account) {
                return new ExternalAccount(account);
            }));
        }).fail(function(xhr, status, error) {
            Raven.captureMessage('Error while updating addon account', {
                url: url, status: status, error: error
            });
        });
    };

    self.updateAccounts()
};

function initAddonSettings() {
    var elements = $('.addon-oauth');
    ko.utils.arrayMap(elements, function(elem) {
        ko.applyBindings(
            new OAuthAddonSettingsViewModel(
                $(elem).data('addon-short-name'),
                $(elem).data('addon-name')
            ), elem
        );
    });
}

initAddonSettings();