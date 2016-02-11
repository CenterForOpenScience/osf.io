'use strict';
var ko = require('knockout');

var $osf = require('js/osfHelpers');

var ViewModel = function() {
    var self = this;
    self.instNames = ko.observableArray([]);
    self.selectedInst = ko.observable();
    self.insts = {};
    $osf.ajaxJSON(
        'GET',
        window.contextVars.apiV2Prefix + 'institutions/',
        {
            isCors: true
        }
    ).done( function(response){
        for (var i = 0; i < response.data.length; i++){
            var name = response.data[i].attributes.name;
            self.instNames.push(name);
            self.insts[name] = response.data[i].attributes.auth_url;
        }
    }).fail(function(response){
    });

    self.instLogin = function(){
        window.location = self.insts[self.selectedInst()];
    };
};

var InstitutionSignIn = function(selector) {
    $osf.applyBindings(new ViewModel(), selector);
};

module.exports = InstitutionSignIn;

