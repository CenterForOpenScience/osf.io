'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var OAuthAddonSettingsViewModel = require('../rdmAddonSettings.js').OAuthAddonSettingsViewModel;
var oop = require('js/oop');

var ViewModel = oop.extend(OAuthAddonSettingsViewModel, {
    constructor: function(url, institutionId) {
        this.super.constructor.call(this, 'iqbrims', 'IQB-RIMS', institutionId);

        this.managementProjectGUID = ko.observable('');
        this.managementProjectURL = ko.observable('');
        this.managementProjectRegex = /^https?:\/\/[^\/]+?\/([^\/]+?)\/?$/;
        this.isValidManagementProjectURL = ko.pureComputed(function() {
            var url = this.managementProjectURL().trim();
            return this.managementProjectRegex.test(url);
        }, this);
        this.isSavingManagementProject = ko.observable(false);
        this.canSaveManagementProject = ko.pureComputed(function() {
            return this.isValidManagementProjectURL() &&
                !this.isSavingManagementProject();
        }, this);
    },

    saveManagementProject: function() {
        this.isSavingManagementProject(true);
        var projectUrl = this.managementProjectURL().trim();
        var matched = projectUrl.match(this.managementProjectRegex);
        if (!matched) {
            throw new Error('Invalid management URL: ' + projectUrl);
        }
        var guid = matched[1];

        var url = '/addons/api/v1/settings/' + this.name + '/' + this.institutionId + '/manage/';
        var request = $.ajax({
            url: url,
            type: 'PUT',
            data: JSON.stringify({guid: guid}),
            contentType: 'application/json',
            dataType: 'json'
        });
        var self = this;
        request.done(function() {
            var fetchRequest = self.fetchManagementProject();
            fetchRequest.done(function() {
                self.managementProjectURL('');
                self.setMessage('Saving management project was successful', 'text-success');
                self.isSavingManagementProject(false);
            });
            fetchRequest.fail(function() {
                self.setMessage('Error while saving management project', 'text-danger');
                self.isSavingManagementProject(false);
            });
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while saving addon management project', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            self.setMessage('Error while saving management project', 'text-danger');
            self.isSavingManagementProject(false);
        });
        return request;
    },

    removeManagementProject: function() {
        var url = '/addons/api/v1/settings/' + this.name + '/' + this.institutionId + '/manage/';
        var request = $.ajax({
            url: url,
            type: 'DELETE',
            dataType: 'json'
        });
        var self = this;
        request.done(function() {
            var fetchRequest = self.fetchManagementProject();
            fetchRequest.done(function() {
                self.managementProjectURL('');
                self.setMessage('Removing management project was successful', 'text-success');
            });
            fetchRequest.fail(function() {
                self.setMessage('Error while removing management project', 'text-danger');
            });
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while removing addon management project', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
            self.setMessage('Error while removing management project', 'text-danger');
        });
        return request;
    },

    fetchManagementProject: function(){
        var url = '/addons/api/v1/settings/' + this.name + '/' + this.institutionId + '/manage/';
        var request = $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        });
        var self = this;
        request.done(function(data) {
            self.managementProjectGUID(data.guid);
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while fetching addon management project', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
        return request;
    }
});

function IQBRIMSUserConfig(selector, url, institutionId) {
    var viewModel = new ViewModel(url, institutionId);
    ko.applyBindings(viewModel, $(selector)[0]);
    viewModel.fetchManagementProject()
        .fail(function() {
            viewModel.setMessage('Error while fetching management project', 'text-danger');
        });
}

module.exports = {
    IQBRIMSViewModel: ViewModel,
    IQBRIMSUserConfig: IQBRIMSUserConfig
};
