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
var osfHelpers = require('js/osfHelpers');
var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');
var NodesPrivacyTreebeard = require('js/nodesPrivacySettingsTreebeard');

var ctx = window.contextVars;

var NODE_OFFSET = 25;

var API_BASE = 'http://localhost:8000/v2/nodes/'

var MESSAGES = {
    makeProjectPublicWarning: 'Please review your project for sensitive or restricted information before making it public.  ' +
                        'Once a project is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    makeProjectPrivateWarning: 'Making a project private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeComponentPublicWarning: '<p>Please review your component for sensitive or restricted information before making it public.</p>' +
                        'Once a component is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    makeComponentPrivateWarning: 'Making a component private will prevent users from viewing it on this site, ' +
                        'but will have no impact on external sites, including Google\'s cache. ' +
                        'Would you like to continue?',

    makeRegistrationPublicWarning: 'Once a registration is made public, you will not be able to make the ' +
                        'registration private again.  After making the registration public, if you '  +
                        'discover material in it that should have remained private, your only option ' +
                        'will be to retract the registration.  This will eliminate the registration, ' +
                        'leaving only basic information of the project title, description, and '  +
                        'contributors with a notice of retraction.',

    addonWarning: 'The following addons will be effected by this change.  Are you sure you want to continue?',

    selectNodes: 'Choose which of your projects and components to make public or private. Checked projects and components will be public, unchecked is private.'
};

function getNodeTree(nodeTree, nodesOriginal) {
    var i;
    var nodeId = nodeTree.node.id;
    var nodeIsPublic = nodeTree.node.is_public;
    nodesOriginal[nodeId] = nodeIsPublic;
    if (nodeTree.children) {
        for (i in nodeTree.children) {
            nodesOriginal = getNodeTree(nodeTree.children[i], nodesOriginal);
        }
    }
    //var localNodes = nodesOriginal;
    return nodesOriginal;
}

function patchNodePrivacy(node, isPublic) {
    var url = API_BASE + node + '/';
    $.ajax({
        url: url,
        type: 'PATCH',
        dataType: 'json',
        contentType: 'application/json',
        crossOrigin: true,
        xhrFields: { withCredentials: true},
        processData: false,
        data: JSON.stringify(
            {'data': {
               'type': 'nodes',
               'id':   node,
               'attributes': {
                   'public': isPublic
               }
        }
        })
    }).done(function(response) {
        window.location.reload();
    }).fail(function(xhr, status, error) {
        //$privacysMsg.addClass('text-danger');
        //$privacysMsg.text('Could not retrieve project settings.');
        Raven.captureMessage('Could not PATCH project settings.', {
            url: url,  status: status, error: error
        });
    });
}

//function getNodeTree(nodeTree, nodesOriginal) {
//    var i;
//    var nodeId = nodeTree.node.id;
//    var nodeIsPublic = nodeTree.node.is_public;
//    var addons = nodeTree.node.addons;
//    nodesOriginal[nodeId] = {
//        isPublic: nodeIsPublic,
//        addons: addons
//    };
//    if (nodeTree.children) {
//        for (i in nodeTree.children) {
//            nodesOriginal = getNodeTree(nodeTree.children[i], nodesOriginal);
//        }
//    }
//    //var localNodes = nodesOriginal;
//    return nodesOriginal;
//}

//function getAddons(nodeTree, addons) {
//    var nodeAddons = [];
//    var i;
//    debugger
//    nodeAddons = nodeTree.node.addons;
//    //for (i=0; i < nodeAddons.length; i++) {
//    //    console.log('nodeAddons[i] is ' + nodeAddons[i]);
//    //}
//    addons.push(nodeTree.node.addons);
//    if (nodeTree.children) {
//        for (i in nodeTree.children) {
//            addons = getAddons(nodeTree.children[i], addons);
//        }
//    }
//    //var localNodes = nodesOriginal;
//    return addons;
//}
//
var NodesPrivacyViewModel = function() {
    var self = this;
    var nodesOriginal = {};
    var addons = [];

    self.nodesState = ko.observable({});

    self.nodesState.subscribe(function(newValue) {
        console.log('nodesState is ' + JSON.stringify(newValue));
        m.redraw(true);
    });

    self.addons = ko.observable();

    self.nodeParent = ko.observable();

    self.nodesChanged = ko.observable({});

    self.nodesChanged.subscribe(function(newValue) {
        console.log('nodesChanged is ' + JSON.stringify(newValue));
        console.log('nodesOriginal is ' + JSON.stringify(nodesOriginal));
    });

    var $privacysMsg = $('#configurePrivacyMessage');
    var treebeardUrl = ctx.node.urls.api  + 'get_node_tree/';

    $('#nodesPrivacy').on('hidden.bs.modal', function () {
        self.clear();
    });

    $.ajax({
        url: treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        response[0].node.is_public = true;
        self.nodeParent(response[0].node.id);
        self.addons(response[0].addons);
        //addons = getAddons(response[0], addons);
        nodesOriginal = getNodeTree(response[0], nodesOriginal);
        self.nodesState(nodesOriginal);
        new NodesPrivacyTreebeard(response, self.nodesState, self.nodesChanged, nodesOriginal);
        //patchNodePrivacy('uxgdq', true);
    }).fail(function(xhr, status, error) {
        $privacysMsg.addClass('text-danger');
        $privacysMsg.text('Could not retrieve project settings.');
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
        self.page('addon');
    };

    self.confirmChanges =  function() {
        var nodesChanged = ko.toJS(self.nodesChanged);
        for (var node in nodesChanged) {
            patchNodePrivacy(node, nodesChanged[node]);
        }
    };

    self.clear = function() {
        self.page('warning');
        self.nodesChanged({});
        self.nodesState(nodesOriginal);
    };

    self.selectAll = function() {
        var node;
        var nodesState = ko.toJS(self.nodesState());
        var nodesChanged = ko.toJS(self.nodesChanged());
        for (node in nodesState) {
            nodesState[node] = true;
            if (!nodesOriginal[node]) {
                nodesChanged[node] = true;
            }
            else if (typeof (nodesChanged[node])) {
                delete nodesChanged[node];
            }
        }
        self.nodesState(nodesState);
        self.nodesChanged(nodesChanged);
        m.redraw(true);
    };

    self.selectNone = function() {
        var node;
        var nodesState = ko.toJS(self.nodesState());
        var nodesChanged = ko.toJS(self.nodesChanged());
        for (node in nodesState) {
            nodesState[node] = false;
            if (nodesOriginal[node]) {
                nodesChanged[node] = false;
            }
            else if (typeof (nodesChanged[node])) {
                delete nodesChanged[node];
            }
        }

        self.nodesState(nodesState);
        self.nodesChanged(nodesChanged);
        m.redraw(true);
    };

};

function NodesPrivacy (selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.data = data;
    self.viewModel = new NodesPrivacyViewModel(self.data);
    self.init();


}

NodesPrivacy.prototype.init = function() {
    var self = this;
    osfHelpers.applyBindings(self.viewModel, this.selector);

};

module.exports = {
    _ProjectViewModel: NodesPrivacyViewModel,
    NodesPrivacy: NodesPrivacy
};
