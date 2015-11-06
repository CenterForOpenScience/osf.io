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
var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
var NodesPrivacyTreebeard = require('js/nodesPrivacySettingsTreebeard');

var NODE_OFFSET = 25;

//Todo (billyhunt): change url to dev or production as needed
var API_BASE = 'http://localhost:8000/v2/nodes/';

var MESSAGES = {
    makeProjectPublicWarning: 'Please review your project for sensitive or restricted information before making it public.  ' +
                        'Once a project is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        '<br><br>Making a project private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Are you sure you would like to continue?',

    selectNodes: 'Please select the components you’d like to make <b>public</b> by checking the boxes below. ' +
                        'Checked components will be <b>public</b>; unchecked components will be <b>private</b>.',

    addonWarning: 'The following addons will be effected by this change.',
};

function getNodesOriginal(nodeTree, nodesOriginal) {
    /**
     * take treebeard tree structure of nodes and get a dictionary of parent node and its
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

//function patchNodesPrivacy(nodes) {
//    /**
//     * patche all the nodes in a changed state.
//     * we will use API V2 bulk requests when it becomes available
//     */
//    var promise;
//    for (var key in nodes) {
//        var node = nodes[key];
//        var url = API_BASE + node.id + '/';
//        nodesPatch = []
//        nodesPatch.push({
//        JSON.stringify(
//            {
//                'data': {
//                    'type': 'nodes',
//                    'id': node.id,
//                    'attributes': {
//                        'public': node.public
//                    }
//                }
//            })}
//        });
//    }
//
//        promise = $.when(promise,
//            $.ajax({
//                url: url,
//                type: 'PATCH',
//                dataType: 'json',
//                contentType: 'application/json',
//                crossOrigin: true,
//                xhrFields: {withCredentials: true},
//                processData: false,
//                data: JSON.stringify(
//                    {
//                        'data': {
//                            'type': 'nodes',
//                            'id': node.id,
//                            'attributes': {
//                                'public': node.public
//                            }
//                        }
//                    })
//            }).done(function (response) {
//            }).fail(function (xhr, status, error) {
//                $osf.growl('Error', 'Unable to update Projects and/or Components');
//                Raven.captureMessage('Could not PATCH project settings.', {
//                    url: url, status: status, error: error
//                });
//            }));
//
//
//    return promise;
//
//}

function patchNodesPrivacy(nodes) {
    /**
     * patche all the nodes in a changed state.
     * we will use API V2 bulk requests when it becomes available
     */
    var promise;
    for (var key in nodes) {
        var node = nodes[key];
        var url = API_BASE + node.id + '/';

        promise = $.when(promise,
            $.ajax({
                url: url,
                type: 'PATCH',
                dataType: 'json',
                contentType: 'application/json',
                crossOrigin: true,
                xhrFields: {withCredentials: true},
                processData: false,
                data: JSON.stringify(
                    {
                        'data': {
                            'type': 'nodes',
                            'id': node.id,
                            'attributes': {
                                'public': node.public
                            }
                        }
                    })
            }).done(function (response) {
            }).fail(function (xhr, status, error) {
                $osf.growl('Error', 'Unable to update Projects and/or Components');
                Raven.captureMessage('Could not PATCH project settings.', {
                    url: url, status: status, error: error
                });
            }));

    }
    return promise;

}

var NodesPrivacyViewModel = function(data, parentIsPublic) {
    /**
     * view model which corresponds to nodes_privacy.mako (#nodesPrivacy)
     *
     * @type {NodesPrivacyViewModel}
     */
    var self = this;
    var nodesOriginal = {};

    self.nodesState = ko.observableArray();
    /**
     * state of current nodes
     */
    self.nodesState.subscribe(function(newValue) {
        m.redraw(true);
    });

    self.nodesOriginal = ko.observableArray();
    /**
     * original node state on page load
     */
    self.nodesOriginal.subscribe(function(newValue) {
    });
    /**
     * id of parent node
     */

    //Parent node is public or not
    var treebeardUrl = data.node.api_url  + 'get_node_tree/';
    /**
     * get node free for treebeard from API V1
     */
    $.ajax({
        url: treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        var nodeParent = {};
        nodesOriginal = getNodesOriginal(response[0], nodesOriginal);
        self.nodesOriginal(nodesOriginal);
        var nodesState = $.extend(true, {}, nodesOriginal);
        nodeParent = response[0].node.id;
        //change node state to reflect button push by user on project page (make public | make private)
        nodesState[nodeParent].public = !parentIsPublic;
        nodesState[nodeParent].changed = true;
        self.nodesState(nodesState);
        new NodesPrivacyTreebeard(response, self.nodesState, nodesOriginal);
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
            addon: 'Addons Effected'
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
        /**
         * confirmChanges forces a promise to make sure all requests are returned before
         * reloading the page
         */
        var nodesState = ko.toJS(self.nodesState());
        var promise = patchNodesPrivacy(nodesState);
        promise.then(function () {
            window.location.reload();
        });
    };

    self.clear = function() {
        self.page('warning');
        self.nodesState(self.nodesOriginal());
    };

    self.selectAll = function() {
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            nodesState[node].public = true;
            if (nodesState[node].public !== nodesOriginal[node].public) {
                nodesState[node].changed = true;
            }
            else {
                nodesState[node].changed = false;
            }
        }
        self.nodesState(nodesState);
        m.redraw(true);
    };

    self.selectNone = function() {
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            nodesState[node].public = false;
            if (nodesState[node].public !== nodesOriginal[node].public) {
                nodesState[node].changed = true;
            }
            else {
                nodesState[node].changed = false;
            }
        }
        self.nodesState(nodesState);
        m.redraw(true);
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
