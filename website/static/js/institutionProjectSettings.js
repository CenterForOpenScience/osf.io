'use strict';
var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

var ViewModel = function(data) {
    var self = this;
    self.primaryInstitution = ko.observable('Loading...');
    self.loading = ko.observable(true);
    self.institutionHref = ko.observable('');
    self.availableInstitutions = ko.observable(false);
    self.selectedInstitution = ko.observable();

    self.fetchUserInstitutions = function() {
        var url = data.apiV2Prefix + 'users/' + data.currentUser.id + '/?embed=institutions';
        return $osf.ajaxJSON(
            'GET',
            url,
            {isCors: true}
        ).done(function (response) {
            if (response.data.embeds.institutions.data.length){
                self.availableInstitutions(response.data.embeds.institutions.data);
                self.loading(false);
            }
        }).fail(function (xhr, status, error) {
            Raven.captureMessage('Unable to fetch user with embedded institutions', {
                url: url,
                status: status,
                error: error
            });
        });
    };
    self.fetchNodeInstitutions = function() {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/?embed=primary_institution';
        return $osf.ajaxJSON(
            'GET',
            url,
            {isCors: true}
        ).done(function (response) {
            if (response.data.embeds.primary_institution.data) {
                self.primaryInstitution(response.data.embeds.primary_institution.data.attributes.name);
                self.institutionHref(response.data.embeds.primary_institution.data.links.html);
            }
        }).fail(function (xhr, status, error) {
            Raven.captureMessage('Unable to fetch node with embedded institutions', {
                url: url,
                status: status,
                error: error
            });
        });
    };
    self.submitInst = function() {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institution/';
        var inst = self.selectedInstitution();
        return $osf.ajaxJSON(
            'PUT',
            url,
            {
                'isCors': true,
                'data': {
                     'data': {'type': 'institutions', 'id': inst}
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function (response) {
            window.location.reload();
        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to add institution to this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to add institution to this node', {
                url: url,
                status: status,
                error: error
            });
        });
    };
    self.clearInst = function() {
        var url = data.apiV2Prefix + 'nodes/' + data.node.id + '/relationships/institution/';
        return $osf.ajaxJSON(
            'PUT',
            url,
            {
                'isCors': true,
                'data': {
                     'data': null
                },
                fields: {xhrFields: {withCredentials: true}}
            }
        ).done(function (response) {
            window.location.reload();
        }).fail(function (xhr, status, error) {
            $osf.growl('Unable to remove institution from this node. Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
            Raven.captureMessage('Unable to remove institution from this node!', {
                url: url,
                status: status,
                error: error
            });
        });
    };
};

var InstitutionProjectSettings = function(selector, data)  {
    this.viewModel = new ViewModel(data);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.fetchUserInstitutions();
    this.viewModel.fetchNodeInstitutions();
};

module.exports = InstitutionProjectSettings;
