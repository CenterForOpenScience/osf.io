'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');

var ViewModel = function(data) {
    var self = this;
    self.primaryInstitution = ko.observable('Loading...');
    self.loading = ko.observable(true);
    self.showAdd = ko.observable(false);
    self.institutionHref = ko.observable('');
    self.userInstitutions = window.contextVars.currentUser.institutions;
    self.userInstitutionsIds = self.userInstitutions.map(function(item){return item.id;});
    self.selectedInstitution = ko.observable();
    self.affiliatedInstitutions = ko.observable(window.contextVars.node.institutions);

    var affiliatedInstitutionsIds = self.affiliatedInstitutions().map(function(item){return item.id;});
    self.availableInstitutions = ko.observable(self.userInstitutions.filter(function(each){
        return ($.inArray(each.id, affiliatedInstitutionsIds)) === -1;
    }));

    self.hasThingsToAdd = ko.computed(function(){
        return self.availableInstitutions().length ? true : false;
    });

    self.toggle = function() {
        self.showAdd(self.showAdd() ? false : true);
    };

    self.submitInst = function() {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';
        var inst = self.selectedInstitution();

        return $osf.ajaxJSON(
            'POST',
            url,
            {
                'isCors': true,
                'data': {
                     'data': [{'type': 'institutions', 'id': inst}]
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function (response) {
            var indexes = self.availableInstitutions().map(function(each){return each.id;});
            var index = indexes.indexOf(self.selectedInstitution());
            var added = self.availableInstitutions().splice(index, 1)[0];
            self.availableInstitutions(self.availableInstitutions());
            self.affiliatedInstitutions().push(added);
            self.affiliatedInstitutions(self.affiliatedInstitutions());
            self.showAdd(false);
        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to add institution to this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to add institution to this node', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };
    self.clearInst = function(item) {
        bootbox.confirm({
            title: 'Are you sure you want to remove institutional affiliation from your project?',
            message: 'You are about to remove affiliation with ' + item.name + ' from this project. ' + item.name + ' branding will not longer appear on this project, and the project will not be discoverable on the ' + item.name + ' landing page.',
            callback: function (confirmed) {
                if (confirmed) {
                    self._clearInst(item);
                }
            },
            buttons:{
                confirm:{
                    label:'Remove affiliation'
                }
            }
        });
    };
    self._clearInst = function(item) {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institutions/';
        return $osf.ajaxJSON(
            'DELETE',
            url,
            {
                isCors: true,
                data: {
                     'data': [{'type': 'institutions', 'id': item.id}]
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function (response) {
            var indexes = self.affiliatedInstitutions().map(function(each){return each.id;});
            var removed = self.affiliatedInstitutions().splice(indexes.indexOf(item.id), 1)[0];
            if ($.inArray(removed.id, self.userInstitutionsIds) >= 0){
                self.availableInstitutions().push(removed);
                self.availableInstitutions(self.availableInstitutions());
            }
            self.affiliatedInstitutions(self.affiliatedInstitutions());
        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to remove institution from this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to remove institution from this node!', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };
};

var InstitutionProjectSettings = function(selector, data)  {
    this.viewModel = new ViewModel(data);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = InstitutionProjectSettings;
