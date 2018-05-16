'use strict';

var $ = require('jquery');
var Raven = require('raven-js');
var ko = require('knockout');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var ChangeMessageMixin = require('js/changeMessage');
var language = require('js/osfLanguage').projectSettings;
var NodesDelete = require('js/nodesDelete').NodesDelete;

var ProjectSettings = oop.extend(
    ChangeMessageMixin,
    {
        constructor: function(params) {
            this.super.constructor.call(this);
            var self = this;

            self.title = ko.observable(params.currentTitle).extend({
                required: {
                    params: true,
                    message: 'Title cannot be blank.'
                }});
            self.description = ko.observable(params.currentDescription);
            self.titlePlaceholder = params.currentTitle;
            self.descriptionPlaceholder = params.currentDescription;

            self.categoryOptions = params.categoryOptions;
            self.categoryPlaceholder = params.category;
            self.selectedCategory = ko.observable(params.category);

            if (!params.updateUrl) {
                throw new Error(language.instantiationErrorMessage);
            }

            self.updateUrl = params.updateUrl;
            self.node_id = params.node_id;

            self.selectedTimestampPattern = ko.observable(params.timestampPattern);
            self.timestampPatternPlaceholder = params.timestampPattern;

            self.originalProjectSettings = ko.observable(self.serialize());
            self.dirty = ko.pureComputed(function(){
                return JSON.stringify(self.originalProjectSettings()) !== JSON.stringify(self.serialize());
            });
        },
        /*error handler*/
        updateError: function(xhr, status, error) {
            var self = this;
            var errorMessage;
            if (error === 'BAD REQUEST') {
                self.changeMessage(language.updateErrorMessage400, 'text-danger');
                errorMessage = language.updateErrorMessage400;
            }
            else {
                self.changeMessage(language.updateErrorMessage, 'text-danger');
                errorMessage = language.updateErrorMessage;
            }
            Raven.captureMessage(errorMessage, {
                extra: {
                    url: self.updateUrl,
                    textStatus: status,
                    err: error
                }
            });
        },
        /*update handler*/
        updateAll: function() {
            var self = this;
            if (!self.dirty()){
                self.changeMessage(language.updateSuccessMessage, 'text-success');
                return;
            }
            var requestPayload = JSON.stringify(self.serialize());
            var request = $.ajax({
                    url: self.updateUrl,
                    type: 'PATCH',
                    dataType: 'json',
                    contentType: 'application/vnd.api+json',
                    crossOrigin: true,
                    xhrFields: {withCredentials: true},
                    processData: false,
                    data: requestPayload
                });
            request.done(function(response) {
                self.categoryPlaceholder = response.data.attributes.category;
                self.titlePlaceholder = response.data.attributes.title;
                self.descriptionPlaceholder = response.data.attributes.description;
                self.timestampPatternPlaceholder = self.selectedTimestampPattern();
                self.selectedCategory(self.categoryPlaceholder);
                self.selectedTimestampPattern(self.timestampPatternPlaceholder);
                self.title(self.titlePlaceholder);
                self.description(self.descriptionPlaceholder);
                self.originalProjectSettings(self.serialize());
                self.changeMessage(language.updateSuccessMessage, 'text-success');
            });
            request.fail(self.updateError.bind(self));
            return request;
        },
        setCategory: function(category){
            var self = this;
            self.selectedCategory(category);
        },
        /*cancel handler*/
        cancelAll: function() {
            var self = this;
            self.selectedCategory(self.categoryPlaceholder);
            self.title(self.titlePlaceholder);
            self.description(self.descriptionPlaceholder);
            self.selectedTimestampPattern(self.timestampPatternPlaceholder);
            self.resetMessage();
        },
        serialize: function() {
            var self = this;
            return {
                data: {
                    type: 'nodes',
                    id:   self.node_id,
                    attributes: {
                        title: self.title(),
                        category: self.selectedCategory(),
                        description: self.description(),
                        timestampPattern: self.selectedTimestampPattern(),
                    }
                }
            };
        }
    });

// TODO: Pass this in as an argument rather than relying on global contextVars
var nodeApiUrl = window.contextVars.node.urls.api;

// Request the first 5 contributors, for display in the deletion modal
var contribs = [];
var moreContribs = 0;

var contribURL = nodeApiUrl + 'get_contributors/?limit=5';
var request = $.ajax({
    url: contribURL,
    type: 'get',
    dataType: 'json'
});
request.done(function(response) {
    // TODO: Remove reliance on contextVars
    var currentUserName = window.contextVars.currentUser.fullname;
    contribs = response.contributors.filter(function(contrib) {
        return contrib.shortname !== currentUserName;
    });
    moreContribs = response.more;
});
request.fail(function(xhr, textStatus, err) {
    Raven.captureMessage('Error requesting contributors', {
        extra: {
            url: contribURL,
            textStatus: textStatus,
            err: err,
        }
    });
});

/**
 * Pulls a random name from the scientist list to use as confirmation string
 *  Ignores case and whitespace
 */
var getConfirmationCode = function(nodeType, isPreprint) {

    var preprint_message = '<p class="danger">This ' + nodeType + ' contains a preprint. Deleting this ' +
        nodeType + ' will also delete your preprint. This action is irreversible.</p>';

    // It's possible that the XHR request for contributors has not finished before getting to this
    // point; only construct the HTML for the list of contributors if the contribs list is populated
    var message = '<p>It will no longer be available to other contributors on the project.' +
        (isPreprint ? preprint_message : '');

    $osf.confirmDangerousAction({
        title: 'Are you sure you want to delete this ' + nodeType + '?',
        message: message,
        callback: function () {
            var request = $.ajax({
                type: 'DELETE',
                dataType: 'json',
                url: nodeApiUrl
            });
            request.done(function(response) {
                // Redirect to either the parent project or the dashboard
                window.location.href = response.url;
            });
            request.fail($osf.handleJSONError);
        },
        buttons: {
            success: {
                label: 'Delete'
            }
        }
    });
};

module.exports = {
    ProjectSettings: ProjectSettings,
    getConfirmationCode: getConfirmationCode
};
