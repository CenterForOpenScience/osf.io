'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var OAuthAddonSettingsViewModel = require('../rdmAddonSettings.js').OAuthAddonSettingsViewModel;
var oop = require('js/oop');

var _ = require('js/rdmGettext')._;

var projectUrlRegex = /^https?:\/\/[^\/]+?\/([^\/]+?)\/?$/;

var ViewModel = oop.extend(OAuthAddonSettingsViewModel, {
    constructor: function(url, institutionId) {
        this.super.constructor.call(this, 'iqbrims', 'IQB-RIMS', institutionId);

        this.managementProjectGUID = ko.observable('');
        this.managementProjectURL = ko.observable('');
        this.isValidManagementProjectURL = ko.pureComputed(function() {
            return projectUrlRegex.test(this.managementProjectURL().trim())
        }, this);
        this.isSavingManagementProject = ko.observable(false);
        this.canSaveManagementProject = ko.pureComputed(function() {
            return this.isValidManagementProjectURL() &&
                !this.isSavingManagementProject();
        }, this);

        this.organizationalProjectGUID = ko.observable('');
        this.organizationalProjectURL = ko.observable('');
        this.isValidOrganizationalProjectURL = ko.pureComputed(function() {
            return projectUrlRegex.test(this.organizationalProjectURL().trim())
        }, this);
        this.isSavingOrganizationalProject = ko.observable(false);
        this.canSaveOrganizationalProject = ko.pureComputed(function() {
            return this.isValidOrganizationalProjectURL() &&
                !this.isSavingOrganizationalProject();
        }, this);
    },

    saveManagementProject: function() {
        var self = this;
        self.isSavingManagementProject(true);
        var projectUrl = self.managementProjectURL().trim();
        var matched = projectUrl.match(projectUrlRegex);
        if (!matched) {
            throw new Error(_('Invalid management URL: ') + projectUrl);
        }
        var guid = matched[1];

        var url = '/addons/api/v1/settings/' + this.name + '/' + this.institutionId + '/manage/';
        return $.ajax({
            url: url,
            type: 'PUT',
            data: JSON.stringify({guid: guid}),
            contentType: 'application/json',
            dataType: 'json'
        }).then(function() {
            return self.fetchManagementProject();
        }).done(function() {
            self.managementProjectURL('');
            self.setMessage(_('Saving management project was successful'), 'text-success');
        }).fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while saving addon management project'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            if (error === 'Unauthorized' || error === 'Forbidden') {
                self.setMessage(_('Permission error while saving management project'), 'text-danger');
            } else {
                self.setMessage(_('Error while saving management project'), 'text-danger');
            }
        }).always(function() {
            self.isSavingManagementProject(false);
        });
    },

    removeManagementProject: function() {
        var self = this;
        var url = '/addons/api/v1/settings/' + self.name + '/' + self.institutionId + '/manage/';
        return $.ajax({
            url: url,
            type: 'DELETE',
            dataType: 'json'
        }).then(function() {
            return self.fetchManagementProject();
        }).done(function() {
            self.managementProjectURL('');
            self.setMessage(_('Removing management project was successful'), 'text-success');
        }).fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while removing addon management project'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            if (error === 'Unauthorized' || error === 'Forbidden') {
                self.setMessage(_('Permission error while removing management project'), 'text-danger');
            } else {
                self.setMessage(_('Error while removing management project'), 'text-danger');
            }
        });
    },

    fetchManagementProject: function(){
        var self = this;
        var url = '/addons/api/v1/settings/' + self.name + '/' + self.institutionId + '/manage/';
        return $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(data) {
            self.managementProjectGUID(data.guid);
        }).fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while fetching addon management project'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    },

    saveOrganizationalProject: function() {
        var self = this;
        self.isSavingOrganizationalProject(true);
        var projectUrl = self.organizationalProjectURL().trim();
        var matched = projectUrl.match(projectUrlRegex);
        if (!matched) {
            throw new Error('Invalid organizational URL: ' + projectUrl);
        }
        var guid = matched[1];

        var url = '/addons/api/v1/settings/' + this.name + '/' + this.institutionId + '/organization/';
        return $.ajax({
            url: url,
            type: 'PUT',
            data: JSON.stringify({guid: guid}),
            contentType: 'application/json',
            dataType: 'json'
        }).then(function() {
            return self.fetchOrganizationalProject();
        }).done(function() {
            self.organizationalProjectURL('');
            self.setMessage(_('Saving organizational project was successful'), 'text-success');
        }).fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while saving addon organizational project'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            if (error === 'Unauthorized' || error === 'Forbidden') {
                self.setMessage(_('Permission error while saving organizational project'), 'text-danger');
            } else {
                self.setMessage(_('Error while saving organizational project'), 'text-danger');
            }
        }).always(function() {
            self.isSavingOrganizationalProject(false);
        });
    },

    removeOrganizationalProject: function() {
        var self = this;
        var url = '/addons/api/v1/settings/' + self.name + '/' + self.institutionId + '/organization/';
        return $.ajax({
            url: url,
            type: 'DELETE',
            dataType: 'json'
        }).then(function() {
            return self.fetchOrganizationalProject();
        }).done(function() {
            self.organizationalProjectURL('');
            self.setMessage(_('Removing organizational project was successful'), 'text-success');
        }).fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while removing addon organizational project'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            if (error === 'Unauthorized' || error === 'Forbidden') {
                self.setMessage(_('Permission error while removing organizational project'), 'text-danger');
            } else {
                self.setMessage(_('Error while removing organizational project'), 'text-danger');
            }
        });
    },

    fetchOrganizationalProject: function(){
        var self = this;
        var url = '/addons/api/v1/settings/' + self.name + '/' + self.institutionId + '/organization/';
        return $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(data) {
            self.organizationalProjectGUID(data.guid);
        }).fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while fetching addon organization project'), {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    }
});

function IQBRIMSUserConfig(selector, url, institutionId) {
    var viewModel = new ViewModel(url, institutionId);
    ko.applyBindings(viewModel, $(selector)[0]);
    viewModel.fetchManagementProject()
        .fail(function() {
            viewModel.setMessage(_('Error while fetching management project'), 'text-danger');
        });
    viewModel.fetchOrganizationalProject()
        .fail(function() {
            viewModel.setMessage(_('Error while fetching organizational project'), 'text-danger');
        });
}

module.exports = {
    IQBRIMSViewModel: ViewModel,
    IQBRIMSUserConfig: IQBRIMSUserConfig
};
