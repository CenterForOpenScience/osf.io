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
                self.insts[name] = item.attributes.auth_url;
                return name;
            }));
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

