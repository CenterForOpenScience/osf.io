'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var ko = require('knockout');
var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var ChangeMessageMixin = require('js/changeMessage');

var NodeCategoryTitleDescriptionSettings = oop.extend(
    ChangeMessageMixin,
    {
        constructor: function(category, categories, updateUrl, disabled) {
            this.super.constructor.call(this);

            var self = this;
            self.currentNode = window.contextVars.node;
            self.titleDescriptionEditUrl = self.currentNode.api_url;
            self.description = ko.observable(self.currentNode.description);
            self.title = ko.observable(self.currentNode.title);

            self.disabled = disabled || false;

            self.UPDATE_SUCCESS_MESSAGE = 'Category updated successfully';
            self.UPDATE_ERROR_MESSAGE = 'Error updating category, please try again. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.UPDATE_ERROR_MESSAGE_RAVEN = 'Error updating Node.category';

            self.INSTANTIATION_ERROR_MESSAGE = 'Trying to instatiate NodeCategoryTitleDescriptionSettings view model without an update URL';

            self.MESSAGE_SUCCESS_CLASS = 'text-success';
            self.MESSAGE_ERROR_CLASS = 'text-danger';

            if (!updateUrl) {
                throw new Error(self.INSTANTIATION_ERROR_MESSAGE);
            }

            self.categories = categories;
            self.category = ko.observable(category);
            self.updateUrl = updateUrl;

            self.selectedCategory = ko.observable(category);
            self.dirty = ko.observable(false);
            self.selectedCategory.subscribe(function(value) {
                if (value !== self.category()) {
                    self.dirty(true);
                }
            });

            self.dirtyTitle = ko.observable(false);
            self.dirtyDescription = ko.observable(false);
        },

        /*success handlers*/
        updateCategorySuccess: function(newcategory) {
            var self = this;
            self.changeMessage(self.UPDATE_SUCCESS_MESSAGE, self.MESSAGE_SUCCESS_CLASS);
            self.category(newcategory);
            self.dirty(false);
        },
        //TODO - refactor title/description success handlers 
        updateTitleSuccess: function() {
            window.location.reload();
        },
        updateDescriptionSuccess: function() {
            window.location.reload();
        },

        /*error handlers*/
        updateCategoryError: function(xhr, status, error) {
            var self = this;
            self.changeMessage(self.UPDATE_ERROR_MESSAGE, self.MESSAGE_ERROR_CLASS);
            Raven.captureMessage(self.UPDATE_ERROR_MESSAGE_RAVEN, {
                url: self.updateUrl,
                textStatus: status,
                err: error
            });
        },
        updateTitleError: function() {
            document.getElementById('title-input-message').style.color = "#ff0000";
            document.getElementById('title-input-message').innerHTML = 'Title cannot be blank.';
        },
        updateDescriptionError: function() {
            document.getElementById('title-input-message').style.color = "#ff0000";
            document.getElementById('title-input-message').innerHTML = 'Error updating description, please try again.'+ 
            ' If the problem persists, email <a href="mailto:support@osf.io">support@osf.io</a>.';
        },

        /*update handlers*/
        updateCategory: function() {
            var self = this;
            return $osf.putJSON(self.updateUrl, {
                    category: self.selectedCategory()
                })
                .then(function(response) {
                    return response.updated_fields.category;
                })
                .done(self.updateCategorySuccess.bind(self))
                .fail(self.updateCategoryError.bind(self));
        },        
        updateTitle: function() {
            var self = this;
            return $osf.putJSON(self.titleDescriptionEditUrl, {
                    title: self.title(),
                })
                .done(self.updateTitleSuccess.bind(self))
                .fail(self.updateTitleError.bind(self));
        },
        updateDescription: function() {
            var self = this;
            return $osf.putJSON(self.titleDescriptionEditUrl, {
                    description: self.description(),
                })
                .done(self.updateDescriptionSuccess.bind(self))
                .fail(self.updateDescriptionError.bind(self));
        },
        
        /*cancel handlers*/
        cancelUpdateCategory: function() {
            var self = this;
            self.selectedCategory(self.category());
            self.dirty(false);
            self.resetMessage();
        },
        cancelUpdateTitle: function() {
            var self = this;
            self.title(self.currentNode.title);
            self.dirtyTitle(false);
        },
        cancelUpdateDescription: function() {
            var self = this;
            self.description(self.currentNode.description);
            self.dirtyDescription(false);
        }
    });

var ProjectSettings = {
    NodeCategoryTitleDescriptionSettings: NodeCategoryTitleDescriptionSettings
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
        }
    });
};

module.exports = ProjectSettings;
