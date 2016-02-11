'use strict';
var ko = require('knockout');

var $osf = require('js/osfHelpers');
var ctx = window.contextVars;

var ViewModel = function() {
    var self = this;
    self.primaryInstitution = ko.observable('None');
    self.institutionHref = ko.observable('');
    self.availableInstitutions = ko.observable();
    $osf.ajaxJSON(
        'GET',
        ctx.apiV2Prefix + 'users/' + ctx.currentUser.id + '/?embed=institutions',
        {isCors: true}
    ).done(function(response) {
        self.availableInstitutions(response.data.embeds.institutions.data);
    }).fail(function (xhr, status, error) {
        Raven.captureMessage('Error creating comment', {
            url: url,
            status: status,
            error: error
        });
    });
    $osf.ajaxJSON(
        'GET',
        ctx.apiV2Prefix + 'nodes/' + ctx.node.id + '/?embed=primary_institution',
        {isCors: true}
    ).done(function(response) {
        if (response.data.embeds.primary_institution.data){
            self.primaryInstitution(response.data.embeds.primary_institution.data.attributes.name);
            self.institutionHref(response.data.embeds.primary_institution.data.links.html);
        }
    }).fail(function (xhr, status, error) {
        Raven.captureMessage('Error creating comment', {
            url: url,
            status: status,
            error: error
        });
    });
    self.submitInst = function() {
        var url = ctx.apiV2Prefix + 'nodes/' + ctx.node.id + '/relationships/institution/';
        var inst = $('input[name=primaryInst]:checked', '#selectedInst').val();
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
            $osf.growl('Unable to add institution to this node!');
            Raven.captureMessage('Error creating comment', {
                url: url,
                status: status,
                error: error
            });
        });
    };
    self.clearInst = function() {
        var url = ctx.apiV2Prefix + 'nodes/' + ctx.node.id + '/relationships/institution/';
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
            $osf.growl('Unable to remove institution from this node!');
            Raven.captureMessage('Error creating comment', {
                url: url,
                status: status,
                error: error
            });
        });
    };
};

var InstitutionProjectSettings = function(selector)  {
    $osf.applyBindings(new ViewModel(), selector)
};

module.exports = InstitutionProjectSettings;
