/**
 * Controller for the Remove Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var oop = require('./oop');
var $osf = require('./osfHelpers');
var Paginator = require('./paginator');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');

function removeNodesContributors(contributor, nodes) {

    var removeUrl = window.contextVars.node.urls.api + 'contributor/remove/';
    return $osf.postJSON(
        removeUrl, {
            contributorID: contributor,
            nodeIDs: nodes
        });
}


var RemoveContributorViewModel = oop.extend(Paginator, {
    constructor: function(title, nodeId, userName, userId, contribShouter, pageChangedShouter) {
        this.super.constructor.call(this);
        var self = this;
        self.title = title;
        self.nodeId = nodeId;
        self.userId = userId;
        self.contributorToRemove = ko.observable('');
        self.REMOVE = 'remove';
        self.REMOVE_ALL = 'removeAll';
        self.REMOVE_NO_CHILDREN = 'removeNoChildren';
        self.REMOVE_SELF = 'removeSelf';

        //This shouter allows the ContributorsViewModel to share which contributor to remove
        // with the RemoveContributorViewModel
        contribShouter.subscribe(function(newValue) {
            self.contributorToRemove(newValue);
        }, self, 'contribMessageToPublish');

        //This shouter allows RemoveContributorViewModel to know if the
        // ContributorsViewModel is in a dirty state to prevent removal
        self.pageChanged = ko.observable(false);
        pageChangedShouter.subscribe(function(newValue) {
            self.pageChanged(newValue);
        }, self, 'changedMessageToPublish');

        self.page = ko.observable(self.REMOVE);
        self.pageTitle = ko.computed(function() {
            return {
                remove: 'Remove Contributor',
                removeAll: 'Remove Contributor',
                removeNoChildren: 'Remove Contributor'
            }[self.page()];
        });
        self.userName = ko.observable(userName);
        self.deleteAll = ko.observable(false);
        var nodesOriginal = {};
        self.nodesOriginal = ko.observable();
        self.loadingSubmit = ko.observable(false);

        /*
         *   To remove, a contributor, you need one bibliographic contributor
         *   (visibleContributors) one admin, and one registered contributor.
         *   So we make new arrays with the contributor removed, and see if
         *   the results are > 0.
         */
        self.canRemoveNodes = ko.computed(function() {
            var canRemoveNodes = {};
            var nodesOriginalLocal = ko.toJS(self.nodesOriginal());
            if (self.contributorToRemove()) {
                var contributorId = self.contributorToRemove().id;
                for (var key in nodesOriginalLocal) {
                    var node = nodesOriginalLocal[key];
                    var contributorOnNode = false;
                    //User cannot modify the node without admin permissions.
                    if (node.isAdmin || self.removeSelf()) {
                        for (var i = 0; i < node.contributors.length; i++) {
                            if (node.contributors[i].id === self.contributorToRemove().id) {
                                contributorOnNode = true;
                                break;
                            }
                        }
                        var registeredContributors = node.registeredContributors;
                        var adminContributors = node.adminContributors;
                        var visibleContributors = node.visibleContributors;
                        var contributorIndex = node.registeredContributors.indexOf(contributorId);
                        var adminIndex = adminContributors.indexOf(contributorId);
                        var visibleIndex = visibleContributors.indexOf(contributorId);

                        if (contributorIndex > -1) {
                            registeredContributors.splice(contributorIndex, 1);
                        }
                        if (adminIndex > -1) {
                            adminContributors.splice(adminIndex, 1);
                        }
                        if (visibleIndex > -1) {
                            visibleContributors.splice(visibleIndex, 1);
                        }
                        self.canRemoveAdmin = adminContributors.length > 0;
                        self.canRemoveVisible = visibleContributors.length > 0;
                        self.canRemoveRegistered = registeredContributors.length > 0 ;
                        canRemoveNodes[key] = (registeredContributors.length > 0 && adminContributors.length > 0 && visibleContributors.length > 0 && contributorOnNode);
                    }
                    else {
                        canRemoveNodes[key] = false;
                    }
                }
            }
            return canRemoveNodes;
        });

        self.removeSelf = ko.pureComputed(function() {
            return self.contributorToRemove().id === window.contextVars.currentUser.id;
        });

        self.canRemoveNode = ko.computed(function() {
            return self.canRemoveNodes()[self.nodeId];
        });

        self.canRemoveNodesLength = ko.pureComputed(function() {
            return Object.keys(self.canRemoveNodes()).length;
        });

        self.hasChildrenToRemove = ko.computed(function() {
            //if there is more then one node to remove, then show a simplified page
            if (self.canRemoveNodesLength() > 1 && self.titlesToRemove().length > 1) {
                self.page(self.REMOVE);
                return true;
            }
            else {
                self.page(self.REMOVE_NO_CHILDREN);
                return false;
            }
        });

        self.modalSize = ko.pureComputed(function() {
            return self.hasChildrenToRemove() && self.canRemoveNode() ? 'modal-dialog modal-lg' : 'modal-dialog modal-md';
        });

        self.titlesToRemove = ko.computed(function() {
            var titlesToRemove = [];
            for (var key in self.nodesOriginal()) {
                if (self.nodesOriginal().hasOwnProperty(key) && self.canRemoveNodes()[key]) {
                    var node = self.nodesOriginal()[key];
                    var contributors = node.contributors;
                    for (var i = 0; i < contributors.length; i++) {
                        if (contributors[i].id === self.contributorToRemove().id) {
                            titlesToRemove.push(node.title);
                            break;
                        }
                    }
                }
            }
            return titlesToRemove;
        });

        self.titlesToKeep = ko.computed(function() {
            var titlesToKeep = [];
            for (var key in self.nodesOriginal()) {
                if (self.nodesOriginal().hasOwnProperty(key) && !self.canRemoveNodes()[key]) {
                    var node = self.nodesOriginal()[key];
                    var contributors = node.contributors;
                    for (var i = 0; i < contributors.length; i++) {
                        if (contributors[i].id === self.contributorToRemove().id) {
                            titlesToKeep.push(node.title);
                            break;
                        }
                    }
                }
            }
            return titlesToKeep;
        });

        self.nodeIDsToRemove = ko.computed(function() {
            var nodeIDsToRemove = [];
            if (!self.deleteAll()) {
                return [self.nodeId];
            }
            for (var key in self.nodesOriginal()) {
                if (self.nodesOriginal().hasOwnProperty(key) && self.canRemoveNodes()[key]) {
                    var node = self.nodesOriginal()[key];
                    var contributors = node.contributors;
                    for (var i = 0; i < contributors.length; i++) {
                        if (contributors[i].id === self.contributorToRemove().id) {
                            nodeIDsToRemove.push(node.id);
                            break;
                        }
                    }
                }
            }
            return nodeIDsToRemove;
        });

        $.ajax({
            url: window.contextVars.node.urls.api + 'tree',
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            nodesOriginal = projectSettingsTreebeardBase.getNodesOriginal(response[0], nodesOriginal);
            self.nodesOriginal(nodesOriginal);
        }).fail(function(xhr, status, error) {
            $osf.growl('Error', 'Unable to retrieve projects and components');
            Raven.captureMessage('Unable to retrieve projects and components', {
                extra: {
                    url: self.nodeApiUrl, status: status, error: error
                }
            });
        });
    },
    clear: function() {
        var self = this;
        self.deleteAll(false);
    },
    back: function() {
        var self = this;
        self.page(self.REMOVE);
    },
    submit: function() {
        var self = this;
        removeNodesContributors(self.contributorToRemove().id, self.nodeIDsToRemove()).then(function (data) {
            if (data.redirectUrl) {
                window.location.href = data.redirectUrl;
            } else {
                window.location.reload();
            }        }).fail(function(xhr, status, error) {
            $osf.growl('Error', 'Unable to delete Contributor');
            Raven.captureMessage('Could not DELETE Contributor.' + error, {
                extra: {
                    url: window.contextVars.node.urls.api + 'contributor/remove/', status: status, error: error
                }
            });
            self.clear();
            window.location.reload();
        });
    },
    deleteAllNodes: function() {
        var self = this;
        self.page(self.REMOVE_ALL);
    }
});

////////////////
// Public API //
////////////////

function ContribRemover(selector, nodeTitle, nodeId, userName, userId, contribShouter, pageChangedShouter) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.userName = userName;
    self.userId = userId;
    self.viewModel = new RemoveContributorViewModel(self.nodeTitle,
        self.nodeId, self.userName, self.userId, contribShouter, pageChangedShouter);
    self.init();
}

ContribRemover.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    // Clear popovers on dismiss start
    self.$element.on('hide.bs.modal', function() {
        self.$element.find('.popover').popover('hide');
        self.viewModel.clear();
    });
};

module.exports = ContribRemover;
