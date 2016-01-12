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

function getNodesOriginal(nodeTree, nodesOriginal) {
    /**
     * take treebeard tree structure of nodes and get a dictionary of parent node and all its
     * children
     */
    var i;
    var j;
    var adminContributors = [];
    var registeredContributors = [];
    var nodeId = nodeTree.node.id;
    for (i=0; i < nodeTree.node.contributors.length; i++) {
        if (nodeTree.node.contributors[i].is_admin) {
            adminContributors.push(nodeTree.node.contributors[i].id);
        }
        if (nodeTree.node.contributors[i].is_confirmed) {
            registeredContributors.push(nodeTree.node.contributors[i].id);
        }
    }
    nodesOriginal[nodeId] = {
        public: nodeTree.node.is_public,
        id: nodeTree.node.id,
        title: nodeTree.node.title,
        contributors: nodeTree.node.contributors,
        isAdmin: nodeTree.node.is_admin,
        visibleContributors: nodeTree.node.visible_contributors,
        adminContributors: adminContributors,
        registeredContributors: registeredContributors
    };

    if (nodeTree.children) {
        for (j in nodeTree.children) {
            nodesOriginal = getNodesOriginal(nodeTree.children[j], nodesOriginal);
        }
    }
    return nodesOriginal;
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
                remove: 'Delete Contributor',
                removeAll: 'Delete Contributor',
                removeNoChildren: 'Delete Contributor'
            }[self.page()];
        });
        self.userName = ko.observable(userName);
        self.deleteAll = ko.observable(false);
        var nodesOriginal = {};
        self.nodesOriginal = ko.observableArray();
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
                var contributor_id = self.contributorToRemove().id;
                for (var key in nodesOriginalLocal) {
                    var node = nodesOriginalLocal[key];
                    var contributorOnNode = false;
                    //User cannot modify the node without admin permissions.
                    if (node.isAdmin || self.removeSelf) {
                        for (var i = 0; i < node.contributors.length; i++) {
                            if (node.contributors[i].id === self.contributorToRemove().id) {
                                contributorOnNode = true;
                            }
                        }
                        var registeredContributors = node.registeredContributors;
                        var adminContributors = node.adminContributors;
                        var visibleContributors = node.visibleContributors;
                        var contributorIndex = node.registeredContributors.indexOf(contributor_id);
                        var adminIndex = adminContributors.indexOf(contributor_id);
                        var visibleIndex = visibleContributors.indexOf(contributor_id);

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

        self.removeSelf = ko.computed(function() {
            var currentUser = window.contextVars.currentUser.id;
            if (self.contributorToRemove().id === currentUser) {
                return true;
            }
            else {
                return false;
            }
        })

        self.canRemoveNode = ko.computed(function() {
            return self.canRemoveNodes()[self.nodeId];
        });

        self.canRemoveNodesLength = ko.computed(function() {
            var canRemoveNodeLengthLocal = 0;
            for (var key in self.canRemoveNodes()) {
                if (self.canRemoveNodes()[key]) {
                    canRemoveNodeLengthLocal++;
                }
            }
            return canRemoveNodeLengthLocal;
        });

        self.hasChildrenToRemove = ko.computed(function() {
            //if there is more then one node to remove, then show a simplified page
            if (self.canRemoveNodesLength() > 1) {
                self.page(self.REMOVE);
                return true;
            }
            else {
                self.page(self.REMOVE_NO_CHILDREN);
                return false;
            }
        });

        self.modalSize = ko.pureComputed(function() {
            var self = this;
            return self.hasChildrenToRemove() && self.canRemoveNode() ? 'modal-dialog modal-lg' : 'modal-dialog modal-md';
        }, self);

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
            nodesOriginal = getNodesOriginal(response[0], nodesOriginal);
            self.nodesOriginal(nodesOriginal);
        }).fail(function(xhr, status, error) {
            $osf.growl('Error', 'Unable to retrieve projects and components');
            Raven.captureMessage('Unable to retrieve projects and components', {
                url: self.nodeApiUrl, status: status, error: error
            });
        });
    },
    selectRemove: function() {
        var self = this;
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
        var removeUrl = window.contextVars.node.urls.api + 'contributor/remove/';
        $osf.postJSON(
            removeUrl, {
                contributorID: self.contributorToRemove().id,
                nodeIDs: self.nodeIDsToRemove()
            }
        ).done(function(response) {
            // TODO: Don't reload the page here; instead use code below
            if (response.redirectUrl) {
                window.location.href = response.redirectUrl;
            } else {
                window.location.reload();
            }
        }).fail(function (xhr, status, error) {
            $osf.growl('Error', 'Unable to delete Contributor');
            Raven.captureMessage('Could not DELETE Contributor.' + error, {
                url: removeUrl, status: status, error: error
            });
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
