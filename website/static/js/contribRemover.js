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
    var nodeId = nodeTree.node.id;
    nodesOriginal[nodeId] = {
        public: nodeTree.node.is_public,
        id: nodeTree.node.id,
        addons: nodeTree.node.addons,
        title: nodeTree.node.title,
        changed: false
    };

    if (nodeTree.children) {
        for (i in nodeTree.children) {
            nodesOriginal = getNodesOriginal(nodeTree.children[i], nodesOriginal);
        }
    }
    return nodesOriginal;
}

//var getNodeChildrenList = function(nodeId, contributorId) {
//    var self = this;
//    var contribUrl = API_BASE + nodeId + '/contributors/';
//    debugger;
//        $.ajax({
//            url: contribUrl,
//            type: 'GET',
//            crossOrigin: true,
//            xhrFields: {
//                withCredentials: true
//            },
//        }).done(function (response) {
//            for (var i = 0; i < response.data.length; i++) {
//                var node = response.data.length
//                debugger;
//
//            }
//
//            //window.location.reload();
//        }).fail(function (xhr, status, error) {
//            $osf.growl('Error', 'Unable to delete Contributor');
//            Raven.captureMessage('Could not DELETE Contributor.' + error, {
//                API_BASE: url, status: status, error: error
//            });
//        });
//}
//
//


var RemoveContributorViewModel = oop.extend(Paginator, {
    constructor: function(title, nodeId, nodeHasChildren, parentId, parentTitle, userName, shouter) {
        this.super.constructor.call(this);
        var self = this;
        self.title = title;
        self.nodeId = nodeId;
        self.nodeApiUrl = '/api/v1/project/' + self.nodeId + '/';
        self.parentId = parentId;
        self.parentTitle = parentTitle;
        self.contributorToRemove = ko.observable();
        shouter.subscribe(function(newValue) {
            self.contributorToRemove(newValue);
        }, self, 'messageToPublish');

        self.page = ko.observable('remove');
        self.pageTitle = ko.computed(function() {
            return {
                remove: 'Delete Contributor',
                removeAll: 'Delete Contributor'
            }[self.page()];
        });
        self.userName = ko.observable(userName);
        self.deleteAll = ko.observable(false);
        self.nodeHasChildren = ko.observable(nodeHasChildren);
        var nodesOriginal = {};
        self.nodesOriginal = ko.observableArray();

        /**
         * original node state on page load
         */
        self.nodesOriginal.subscribe(function(newValue) {
        });

        /**
         * get node free for treebeard from API V1
         */
        $.ajax({
            url: self.nodeApiUrl,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            nodesOriginal = getNodesOriginal(response[0], nodesOriginal);
            self.nodesOriginal(nodesOriginal);
            debugger;
            ////change node state to reflect button push by user on project page (make public | make private)
            //nodesState[nodeParent].public = !parentIsPublic;
            //nodesState[nodeParent].changed = true;
            //self.nodesState(nodesState);
            //new NodesPrivacyTreebeard(response, self.nodesState, nodesOriginal);
        }).fail(function(xhr, status, error) {
            $osf.growl('Error', 'Unable to retrieve projects and components');
            Raven.captureMessage('Unable to retrieve projects and components', {
                url: self.nodeApiUrl, status: status, error: error
            });
        });
        },
        selectRemove: function() {
            var self = this;
            self.page('remove');
        },
        clear: function() {
            var self = this;
            self.selectRemove();
            self.deleteAll(false);
        },
        deleteOneNode: function() {
            var self = this;
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
            }).fail(function (xhr, status, error) {
                $osf.growl('Error', 'Unable to delete Contributor');
                Raven.captureMessage('Could not DELETE Contributor.' + error, {
                    API_BASE: url, status: status, error: error
                });
            });
            self.page('remove');
        },
        deleteAllNodes: function() {
            var self = this;
            self.page('removeAll');
            //getNodeContributorList(self.nodeId, self.contributorToRemove().id);
        }
});


////////////////
// Public API //
////////////////

function ContribRemover(selector, nodeTitle, nodeId, nodeHasChildren, parentId, parentTitle, userName, shouter) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.nodeTitle = nodeTitle;
    self.nodeId = nodeId;
    self.nodeHasChildren = nodeHasChildren;
    self.parentId = parentId;
    self.parentTitle = parentTitle;
    self.userName = userName;
    self.viewModel = new RemoveContributorViewModel(self.nodeTitle,
        self.nodeId, self.nodeHasChildren, self.parentId, self.parentTitle, self.userName, shouter);
    self.init();
}

ContribRemover.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    // Clear popovers on dismiss start
    self.$element.on('hide.bs.modal', function() {
        self.$element.find('.popover').popover('hide');
        self.clear();
    });
    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    self.$element.on('hidden.bs.modal', function() {
        self.viewModel.clear();
    });
};

module.exports = ContribRemover;
