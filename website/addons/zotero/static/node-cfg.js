var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
require('./node-cfg.css');

var ZoteroAccount = function(display_name, id) {
    var self=this;
    self.display_name = display_name;
    self.id = id;
};

var CitationList = function(name, provider_list_id, provider_account_id ) {
    var self=this;
    self.name = name;
    self.provider_list_id = provider_list_id;
    self.provider_account_id = provider_account_id;
};

var ZoteroSettingsViewModel = function() {
    var self=this;

    self.settings_url = nodeApiUrl + 'zotero/settings/';

    self.accounts = ko.observableArray();
    self.selectedAccountId = ko.observable();
    self.citationLists = ko.observableArray();
    self.selectedCitationList = ko.observable();
    self.message = ko.observable();


    self.updateCitationLists = function(list_id) {
        $.getJSON(
            nodeApiUrl + 'zotero/' + self.selectedAccountId() + '/lists/',
            function(data) {
                self.citationLists(ko.utils.arrayMap(data.citation_lists, function(item) {
                    return new CitationList(item.name, item.provider_list_id, item.provider_account_id);
                }));
                self.selectedCitationList(list_id || self.citationLists()[0].provider_list_id);
            }
        );
    };

    self.selectedAccountId.subscribe(function(value) {
        self.updateCitationLists();
        console.log('working');
    });


    self.save = function() {
        var request = $osf.postJSON(
            self.settings_url,
            {
                external_account_id: self.selectedAccountId(),
                external_list_id: self.selectedCitationList()
            }
        );
        request.done(function(){
            self.message('Settings updated.');
        });
        request.fail(function() {
            self.message('Settings failed');
        });
    };

    self.get = function() {
        $.getJSON(self.settings_url, function(data){
            console.log(data);

            for(var i=0; i < data['accounts'].length; i++) {
                self.accounts.push(new ZoteroAccount(
                    data.accounts[i].display_name,
                    data.accounts[i].id
                ));
            }

            self.selectedAccountId(data.current_account && data.current_account.id || self.selectedAccountId(data.accounts[0].id));
            self.updateCitationLists(data.list_id);
        });
    };

    self.get();



};

////////////////
// Public API //
////////////////

function ZoteroSettings (selector) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.viewModel = new ZoteroSettingsViewModel();
    self.init();
}

ZoteroSettings.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};

//module.exports = ZoteroSettings;
new ZoteroSettings('#addonSettingsZotero');

