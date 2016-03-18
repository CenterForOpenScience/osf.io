'use strict';
var ko = require('knockout');

var $osf = require('js/osfHelpers');
var Raven = require('raven-js');

var ViewModel = function() {
    var self = this;
    self.instNames = ko.observableArray([]);
    self.selectedInst = ko.observable();
    self.loading = ko.observable(true);
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
            var validInsts = response.data.filter(function(item){
                return item.attributes.auth_url;
            });
            self.instNames(
                validInsts.map(function(item){
                    return item.attributes.name;
                }).sort()
            );
            validInsts.forEach(function(item){
                var name = item.attributes.name;
                self.insts[name] = item.attributes.auth_url + '&target=' + encodeURIComponent(window.contextVars.institution_redirect);
                self.insts[item.id] = name;
            });
            var instRedirect = decodeURIComponent(decodeURIComponent(window.contextVars.institution_redirect));
            if (instRedirect){
                var instId = instRedirect.split('institutions')[1];
                instId = instId ? instId.split('/')[1] : false;
                if (instId){
                    self.selectedInst(self.insts[instId]);
                }
            }
            self.loading(false);
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

