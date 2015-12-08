/**
 * Controller for the Add Contributor modal.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var oop = require('./oop');
var $osf = require('./osfHelpers');
var Paginator = require('./paginator');

var API_BASE = 'http://localhost:8000/v2/nodes/';

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
    constructor: function(title, nodeId, nodeHasChildren, parentId, parentTitle, userName, userId, shouter) {
        this.super.constructor.call(this);
        var self = this;
        self.title = title;
        self.nodeId = nodeId;
        self.parentId = parentId;
        self.parentTitle = parentTitle;
        self.userId = userId;
        self.contributorToRemove = ko.observable('');
        shouter.subscribe(function(newValue) {
            self.contributorToRemove(newValue);
        }, self, 'messageToPublish');

        self.page = ko.observable('remove');
        self.pageTitle = ko.computed(function() {
            return {
                remove: 'Delete Contributor',
                removeAll: 'Delete Contributor',
                removeNoChildren: 'Delete Contributor'
            }[self.page()];
        });
        self.userName = ko.observable(userName);
        self.deleteAll = ko.observable(false);
        self.nodeHasChildren = ko.observable(nodeHasChildren);
        var nodesOriginal = {};
        self.nodesOriginal = ko.observableArray();

        self.canRemoveOnNodes = ko.computed(function() {
            var canRemoveOnNodes = {};
            if (self.contributorToRemove()) {
                for (var key in self.nodesOriginal()) {
                    var node = self.nodesOriginal()[key];
                    var registeredContributors = self.nodesOriginal()[key].registeredContributors;
                    var adminContributors = self.nodesOriginal()[key].adminContributors;
                    var visibleContributors = self.nodesOriginal()[key].visibleContributors;
                    var contributorIndex = registeredContributors.indexOf(self.contributorToRemove().id);
                    var adminIndex = adminContributors.indexOf(self.contributorToRemove().id);
                    var visibleIndex = visibleContributors.indexOf(self.contributorToRemove().id);
                    if (contributorIndex > -1) {
                        registeredContributors.splice(contributorIndex, 1);
                    }
                    if (adminIndex > -1) {
                        adminContributors.splice(adminIndex, 1);
                    }
                    if (visibleIndex > -1) {
                        visibleContributors.splice(visibleIndex, 1);
                    }
                    canRemoveOnNodes[key] = (registeredContributors.length > 0 && adminContributors.length > 0 && visibleContributors.length > 0);
                    }
                }
            return canRemoveOnNodes;
        });

        self.canRemoveOnNode = ko.computed(function() {
            return self.canRemoveOnNodes()[self.nodeId];
        })

        self.hasChildrenToRemove = ko.computed(function() {
            //if there is more then one node to remove, then show a simplified page
            if (Object.keys(self.canRemoveOnNodes()).length > 1) {
                self.page('remove');
                return true;
            }
            else {
                self.page('removeNoChildren');
                return false;
            }
        });

        self.modalSize = ko.pureComputed(function() {
            var self = this;
            return self.hasChildrenToRemove() && self.canRemoveAdmin() ? 'modal-dialog modal-lg' : 'modal-dialog modal-md';
        }, self);

        self.titlesToRemove = ko.computed(function() {
            var titlesToRemove = [];
            for (var key in self.nodesOriginal()) {
                if (self.nodesOriginal().hasOwnProperty(key) && self.canRemoveOnNodes()[key]) {
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

        self.nodeIDsToRemove = ko.computed(function() {
            var nodeIDsToRemove = [];
            for (var key in self.nodesOriginal()) {
                if (self.nodesOriginal().hasOwnProperty(key) && self.canRemoveOnNodes()[key]) {
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
            url: window.contextVars.node.urls.api + 'get_node_tree',
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
            self.page('remove');
        },
        submit: function() {
            var self = this;
            if (self.deleteAll()) {
                $osf.postJSON(
                    window.contextVars.node.urls.api + 'contributor/remove/', {
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
                    self.page('remove');
                }).fail(function (xhr, status, error) {
                    $osf.growl('Error', 'Unable to delete Contributor');
                    Raven.captureMessage('Could not DELETE Contributor.' + error, {
                        API_BASE: url, status: status, error: error
                    });
                    self.page('remove');
                });
            }
            else {
                //API V2
                var url = API_BASE + self.nodeId + '/contributors/' + self.contributorToRemove().id + '/';
                $.ajax({
                    url: url,
                    type: 'DELETE',
                    crossOrigin: true,
                    xhrFields: {
                        withCredentials: true
                    },
                }).done(function (response) {
                    window.location.reload();
                    self.page('remove');
                }).fail(function (xhr, status, error) {
                    $osf.growl('Error', 'Unable to delete Contributor');
                    Raven.captureMessage('Could not DELETE Contributor.' + error, {
                        API_BASE: url, status: status, error: error
                    });
                    self.page('remove');
                });
            }
        },
        deleteAllNodes: function() {
            var self = this;
            self.page('removeAll');
        }
});


////////////////
// Public API //
////////////////

function ContribRemover(selector, nodeTitle, nodeId, nodeHasChildren, parentId, parentTitle, userName, userId, shouter) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.nodeHasChildren = nodeHasChildren;
    self.parentId = parentId;
    self.parentTitle = parentTitle;
    self.userName = userName;
    self.userId = userId;
    self.viewModel = new RemoveContributorViewModel(self.nodeTitle,
        self.nodeId, self.nodeHasChildren, self.parentId, self.parentTitle, self.userName, self.userId, shouter);
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
    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    self.$element.on('hidden.bs.modal', function() {
        self.viewModel.clear();
    });
};

module.exports = ContribRemover;
