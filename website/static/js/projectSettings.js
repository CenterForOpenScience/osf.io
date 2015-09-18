'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var ko = require('knockout');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var ChangeMessageMixin = require('js/changeMessage');

var ProjectSettings = oop.extend(
    ChangeMessageMixin,
    {
        constructor: function(params) {
            this.super.constructor.call(this);
            var self = this;

            self.decodedTitle = params.currentTitle;
            self.decodedDescription = $osf.htmlDecode(params.currentDescription);
            self.title = ko.observable(params.currentTitle).extend({
                required: {
                    params: true,
                    message: 'Title cannot be blank.'
                }});
            self.description = ko.observable(self.decodedDescription);

            self.disabled = params.disabled || false;

            self.UPDATE_SUCCESS_MESSAGE = 'Category, title, and description updated successfully';
            self.UPDATE_CATEGORY_ERROR_MESSAGE = 'Error updating category, please try again. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.UPDATE_DESCRIPTION_ERROR_MESSAGE = 'Error updating description, please try again. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.UPDATE_CATEGORY_ERROR_MESSAGE_RAVEN = 'Error updating Node.category';

            self.INSTANTIATION_ERROR_MESSAGE = 'Trying to instantiate ProjectSettings view model without an update URL';

            self.MESSAGE_SUCCESS_CLASS = 'text-success';
            self.MESSAGE_ERROR_CLASS = 'text-danger';

            if (!params.updateUrl) {
                throw new Error(self.INSTANTIATION_ERROR_MESSAGE);
            }

            self.categories = params.categories;
            self.category = params.category;
            self.updateUrl = params.updateUrl;
            self.selectedCategory = ko.observable(params.category);
        },

        /*success handler*/
        updateSuccess: function() {
            var self = this;
            self.changeMessage(self.UPDATE_SUCCESS_MESSAGE, self.MESSAGE_SUCCESS_CLASS);
        },

        /*error handlers*/
        updateCategoryError: function(xhr, status, error) {
            var self = this;
            self.changeMessage(self.UPDATE_CATEGORY_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
            Raven.captureMessage(self.UPDATE_CATEGORY_ERROR_MESSAGE_RAVEN, {
                url: self.updateUrl,
                textStatus: status,
                err: error
            });
        },
        updateDescriptionError: function() {
            var self = this;
            self.changeMessage(self.UPDATE_DESCRIPTION_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
        },

        /*update handlers*/
        updateCategory: function() {
            var self = this;
            return $osf.putJSON(self.updateUrl, {
                    category: self.selectedCategory()
                })
                .then(function(response) {
                    self.category = self.selectedCategory();
                    return response.updated_fields.category;
                })
                .done(self.updateTitle.bind(self))
                .fail(self.updateCategoryError.bind(self));
        },
        updateTitle: function() {
            var self = this;
            return $osf.putJSON(self.updateUrl, {
                    title: self.title()
                })
                .done(function() {
                    self.decodedTitle = self.title();
                },
                self.updateDescription.bind(self));
        },
        updateDescription: function() {
            var self = this;
            return $osf.putJSON(self.updateUrl, {
                    description: self.description()
                })
                .done(function() {
                    self.decodedDescription = self.description();
                },
                self.updateSuccess.bind(self))
                .fail(self.updateDescriptionError.bind(self));
        },

        /*cancel handler*/
        cancelAll: function() {
            var self = this;
            self.selectedCategory(self.category);
            self.title(self.decodedTitle);
            self.description(self.decodedDescription);
            self.resetMessage();
        }
    });

var ProjectSettings = {
    ProjectSettings: ProjectSettings
};

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
        url: contribURL,
        textStatus: textStatus,
        err: err,
    });
});


/**
 * Pulls a random name from the scientist list to use as confirmation string
 *  Ignores case and whitespace
 */
ProjectSettings.getConfirmationCode = function(nodeType) {

    // It's possible that the XHR request for contributors has not finished before getting to this
    // point; only construct the HTML for the list of contributors if the contribs list is populated
    var message = '<p>It will no longer be available to other contributors on the project.';

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

module.exports = ProjectSettings;
