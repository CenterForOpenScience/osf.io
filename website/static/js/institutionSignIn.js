'use strict';
var ko = require('knockout');

var $osf = require('js/osfHelpers');
var Raven = require('raven-js');

var ViewModel = function() {
    var self = this;
    self.instNames = ko.observableArray([]);
    self.selectedInst = ko.observable();
    self.insts = {};
    self.fetchInstitutions = function() {
        var url = window.contextVars.apiV2Prefix + 'institutions/';
        return $osf.ajaxJSON(
            'GET',
            url,
            {
                isCors: true
            }
        ).done(function (response) {
            self.instNames(response.data.map(function(item){
                var name = item.attributes.name;
                self.insts[name] = item.attributes.auth_url + '&target=' + encodeURIComponent(window.contextVars.institution_redirect);
                self.insts[item.id] = name;
                return name;
            }));
            var inst_redirect = decodeURIComponent(decodeURIComponent(window.contextVars.institution_redirect));
            if (inst_redirect){
                var inst_id = inst_redirect.split('institutions')[1];
                inst_id = inst_id ? inst_id.split('/')[1] : false;
                if (inst_id){
                    self.selectedInst(self.insts[inst_id]);
                }
            }
        }).fail(function (xhr, status, error) {
            Raven.captureMessage('Unable to fetch institutions', {
                url: url,
                status: status,
                error: error
            });
        });
    };

    self.instLogin = function(){
        window.location = self.insts[self.selectedInst()];
    };
};

var InstitutionSignIn = function(selector) {
    this.viewModel = new ViewModel();
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.fetchInstitutions();
};

module.exports = InstitutionSignIn;

