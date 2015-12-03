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
    var contributorAdmins = []
    var nodeId = nodeTree.node.id;
    for (i=0; i < nodeTree.node.contributors.length; i++) {
        if (nodeTree.node.contributors[i].is_admin) {
            contributorAdmins.push(nodeTree.node.contributors[i].id);
        }
    }
    nodesOriginal[nodeId] = {
        public: nodeTree.node.is_public,
        id: nodeTree.node.id,
        title: nodeTree.node.title,
        contributors: nodeTree.node.contributors,
        isAdmin: nodeTree.node.is_admin,
        contributorAdmins: contributorAdmins
    };

    if (nodeTree.children) {
        for (j in nodeTree.children) {
            nodesOriginal = getNodesOriginal(nodeTree.children[j], nodesOriginal);
        }
    }
    return nodesOriginal;
}


var RemoveContributorViewModel = oop.extend(Paginator, {
    constructor: function(title, nodeId, nodeHasChildren, parentId, parentTitle, userName, userID, shouter) {
        this.super.constructor.call(this);
        var self = this;
        self.title = title;
        self.nodeId = nodeId;
        self.parentId = parentId;
        self.parentTitle = parentTitle;
        self.userID = userID;
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

        self.canRemoveContributor = ko.computed(function() {
            var canRemoveContributor = {};
            if (self.contributorToRemove()) {
                for (var key in self.nodesOriginal()) {
                    var node = self.nodesOriginal()[key];
                    //If there are contributors that are admin, you can always remove yourself
                    if (node.contributorAdmins.length > 1) {
                        canRemoveContributor[key] = true;
                    }
                    //If there are contributors and you are an admin, you can remove anyone but yourself.
                    else if (node.isAdmin && (self.contributorToRemove().id !== self.userID)) {
                        canRemoveContributor[key] = true;
                    }
                    //If you are not an admin, you can remove yourself and no one else
                    else if (!node.isAdmin && (self.contributorToRemove().id === self.userID)) {
                        canRemoveContributor[key] = true;
                    }
                    else {
                        canRemoveContributor[key] = false;
                    }
                }
            }
            return canRemoveContributor;
        });

        self.hasChildrenToRemove = ko.computed(function() {
            //if there is more then one node to remove, then show a simplified page
            if (Object.keys(self.canRemoveContributor()).length > 1) {
                self.page('remove');
                return true;
            }
            else {
                self.page('removeNoChildren');
                return false;
            }
        });

        self.modalSize = ko.pureComputed(function() {
            return this.hasChildrenToRemove() ? 'modal-dialog modal-lg' : 'modal-dialog modal-md';
        }, self);

        self.titlesToRemove = ko.computed(function() {
            var titlesToRemove = [];
            for (var key in self.nodesOriginal()) {
                if (self.nodesOriginal().hasOwnProperty(key) && self.canRemoveContributor()[key]) {
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
                if (self.nodesOriginal().hasOwnProperty(key) && self.canRemoveContributor()[key]) {
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

function ContribRemover(selector, nodeTitle, nodeId, nodeHasChildren, parentId, parentTitle, userName, userID, shouter) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.nodeHasChildren = nodeHasChildren;
    self.parentId = parentId;
    self.parentTitle = parentTitle;
    self.userName = userName;
    self.userID = userID;
    self.viewModel = new RemoveContributorViewModel(self.nodeTitle,
        self.nodeId, self.nodeHasChildren, self.parentId, self.parentTitle, self.userName, self.userID, shouter);
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
