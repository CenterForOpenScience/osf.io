/**
 * Controller for changing privacy settings for a node and its children.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var oop = require('./oop');
var $osf = require('./osfHelpers');
var Paginator = require('./paginator');
var osfHelpers = require('js/osfHelpers');
var m = require('mithril');
var Treebeard = require('treebeard');
var NodesPrivacyTreebeard = require('js/nodesPrivacySettingsTreebeard');

//Todo (billyhunt): change url to dev or production as needed
var API_BASE = 'http://localhost:8000/v2/nodes/';

var MESSAGES = {
    makeProjectPublicWarning:
                        'Please review your projects, components, and add-ons for sensitive or restricted information before making them public.' +
                        '<br><br>Once they are made public, you should assume they will always be public. You can ' +
                        'return them to private later, but search engines (including Google’s cache) or others may access files before you do.',

    selectNodes: 'Adjust your privacy settings by checking the boxes below. ' +
                        '<br><br><b>Checked</b> projects and components will be <b>public</b>.  <br><b>Unchecked</b> components will be <b>private</b>.',
    addonWarning: {
        nodesPublic: 'The following projects and components will be made <b>public</b>.',
        nodesPrivate: 'The following projects and components will be made <b>private</b>.'
    }
};

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
        canWrite: nodeTree.node.can_write,
        changed: false
    };

    if (nodeTree.children) {
        for (i in nodeTree.children) {
            nodesOriginal = getNodesOriginal(nodeTree.children[i], nodesOriginal);
        }
    }
    return nodesOriginal;
}

function patchNodesPrivacy(nodes) {
    /**
     * patches all the nodes in a changed state
     * uses API v2 bulk requests
     */
    var nodesPatch = [];
    var promise;
    nodesPatch = nodes.splice(0,10).map(function (node) {
        return {
            'type': 'nodes',
            'id': node.id,
            'attributes': {
                'public': node.public
            }
        };
    });
    return $.ajax({
        url: API_BASE,
        type: 'PATCH',
        dataType: 'json',
        contentType: 'application/vnd.api+json; ext=bulk',
        crossOrigin: true,
        xhrFields: {withCredentials: true},
        processData: false,
        data: JSON.stringify({
            data: nodesPatch
        })
    }).done(function (response) {
        if (nodes.length === 0) {
            return;
        }
        return patchNodesPrivacy(nodes);
    });
}

var NodesPrivacyViewModel = function(data, parentIsPublic) {
    /**
     * view model which corresponds to nodes_privacy.mako (#nodesPrivacy)
     *
     * @type {NodesPrivacyViewModel}
     */
    var self = this;
    var nodesOriginal = {};
    var treebeardUrl = data.node.api_url  + 'get_node_tree/';
    self.loadingResults = ko.observable(false);
    //state of current nodes
    self.nodesState = ko.observableArray();
    self.nodesState.subscribe(function(newValue) {
        m.redraw(true);
    });
    //original node state on page load
    self.nodesOriginal = ko.observableArray();
    self.nodesOriginal.subscribe(function(newValue) {
    });

    $('#nodesPrivacy').on('hidden.bs.modal', function () {
        self.clear();
    });

    self.loadingResults(true); // enables spinner
    /**
     * get node tree for treebeard from API V1
     */
    $.ajax({
        url: treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        nodesOriginal = getNodesOriginal(response[0], nodesOriginal);
        self.nodesOriginal(nodesOriginal);
        var nodesState = $.extend(true, {}, nodesOriginal);
        var nodeParent = response[0].node.id;
        //change node state to reflect button push by user on project page (make public | make private)
        nodesState[nodeParent].public = !parentIsPublic;
        nodesState[nodeParent].changed = true;
        self.nodesState(nodesState);
        new NodesPrivacyTreebeard(response, self.nodesState, nodesOriginal);
        self.loadingResults(false);
    }).fail(function(xhr, status, error) {
        $osf.growl('Error', 'Unable to retrieve project settings');
        Raven.captureMessage('Could not GET project settings.', {
            url: treebeardUrl, status: status, error: error
        });
    });

    self.page = ko.observable('warning');

    self.pageTitle = ko.computed(function() {
        return {
            warning: 'Warning',
            select: 'Change Privacy Settings',
            addon: 'Projects and Components Affected'
        }[self.page()];
    });

    self.message = ko.computed(function() {
        return {
            warning: MESSAGES.makeProjectPublicWarning,
            select: MESSAGES.selectNodes,
            addon: MESSAGES.addonWarning
        }[self.page()];
    });

    self.selectProjects =  function() {
        self.page('select');
    };

    self.addonWarning =  function() {
        var nodesState = ko.toJS(self.nodesState);
        self.changedAddons = ko.observableArray([]);
        self.nodesChangedPublic = ko.observableArray([]);
        self.nodesChangedPrivate = ko.observableArray([]);
        var changedAddons = {};
        for (var node in nodesState) {
            if (nodesState[node].changed) {
                if (nodesState[node].addons.length) {
                    for (var i=0; i < nodesState[node].addons.length; i++) {
                        changedAddons[nodesState[node].addons[i]] = true;
                    }
                }
                if (nodesState[node].public) {
                    self.nodesChangedPublic().push(nodesState[node].title);
                }
                else {
                    self.nodesChangedPrivate().push(nodesState[node].title);
                }
            }
        }
        for (var addon in changedAddons) {
            self.changedAddons().push(addon);
        }
        self.page('addon');
    };

    self.confirmChanges =  function() {
        var nodesState = ko.toJS(self.nodesState());
        //patchNodesPrivacy(nodesState);
        nodesState = Object.keys(nodesState).map(function(key) {
            return nodesState[key];
        });
        var nodesChanged = nodesState.filter(function(node) {
            return node.changed;
        });
        patchNodesPrivacy(nodesChanged).then(function () {
            window.location.reload();
        });
    };

    self.clear = function() {
        self.page('warning');
    };

    self.selectAll = function() {
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            if (nodesState[node].canWrite) {
                nodesState[node].public = true;
                if (nodesState[node].public !== nodesOriginal[node].public) {
                    nodesState[node].changed = true;
                }
                else {
                    nodesState[node].changed = false;
                }
            }
        }
        self.nodesState(nodesState);
        m.redraw(true);
    };

    self.selectNone = function() {
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            if (nodesState[node].canWrite) {
                nodesState[node].public = false;
                if (nodesState[node].public !== nodesOriginal[node].public) {
                    nodesState[node].changed = true;
                }
                else {
                    nodesState[node].changed = false;
                }

            }
        }
        self.nodesState(nodesState);
        m.redraw(true);
    };

    self.back = function() {
           var self = this;
            self.page('select');
    };

};

function NodesPrivacy (selector, data, parentNodePrivacy) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.data = data;
    self.viewModel = new NodesPrivacyViewModel(self.data, parentNodePrivacy);
    self.init();

}

NodesPrivacy.prototype.init = function() {
    var self = this;
    osfHelpers.applyBindings(self.viewModel, this.selector);
};

module.exports = {
    _NodesPrivacyViewModel: NodesPrivacyViewModel,
    NodesPrivacy: NodesPrivacy
};
