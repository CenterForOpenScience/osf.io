var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
require('./node-cfg.css');

var ctx = window.contextVars;

var MendeleyAccount = function(display_name, id) {
    this.display_name = display_name;
    this.id = id;
};

var CitationList = function(name, provider_list_id, provider_account_id ) {
    this.name = name;
    this.provider_list_id = provider_list_id;
    this.provider_account_id = provider_account_id;
};

var MendeleySettingsViewModel = function() {

    var self = this;

    self.settings_url = ctx.node.urls.api + 'mendeley/settings/';

    self.accounts = ko.observableArray();
    self.citationLists = ko.observableArray();
    self.selectedAccountId = ko.observable();
    self.selectedCitationList = ko.observable();
    self.message = ko.observable();

    self._requestedCitationList = null;

    self.updateAccounts = function() {
        var url = ctx.node.urls.api + 'mendeley/settings/';
        $.getJSON(url).done(function(data) {
            for (var i=0; i<data.accounts.length; i++) {
                self.accounts.push(new MendeleyAccount(
                    data.accounts[i].display_name,
                    data.accounts[i].id
                ));
            }
            self._requestedCitationList = data.listId;
            self.selectedAccountId(data.currentAccount && data.currentAccount.id || data.accounts[0].id);
        }).fail(function() {
            self.message('Could not load accounts');
        });
    };

    self.updateCitationLists = function() {
        var url = ctx.node.urls.api + 'mendeley/' + self.selectedAccountId() + '/lists/';
        $.getJSON(url).done(function(data) {
            self.citationLists(ko.utils.arrayMap(data.citation_lists, function(item) {
                return new CitationList(item.name, item.provider_list_id, item.provider_account_id);
            }));
            self.selectedCitationList(self._requestedCitationList || data.citation_lists[0].provider_list_id);
        }).fail(function() {
            self.message('Could not load citations');
        });
    };

    self.selectedAccountId.subscribe(function(value) {
        self.updateCitationLists();
    });

    self.updateAccounts();

    self.save = function() {
        var request = $osf.postJSON(
            self.settings_url,
            {
                external_account_id: self.selectedAccountId(),
                external_list_id: self.selectedCitationList()
            }
        ).done(function() {
            self.message('Settings updated.');
        }).fail(function() {
            self.message('Settings failed');
        });
    };

};

////////////////
// Public API //
////////////////

function MendeleySettings (selector) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.viewModel = new MendeleySettingsViewModel();
    self.init();
}

MendeleySettings.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};

//module.exports = MendeleySettings;
new MendeleySettings('#addonSettingsMendeley');

