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
var NodesPrivacyTreebeard = require('js/nodesPrivacySettingsTreebeard');

var ctx = window.contextVars;

var NODE_OFFSET = 25;

var API_BASE = 'http://localhost:8000/v2/nodes/'

var MESSAGES = {
    makeProjectPublicWarning: 'Please review your project for sensitive or restricted information before making it public.  ' +
                        'Once a project is made public, you should assume it will always be public. You can ' +
                        'return it to private later, but search engines or others may access files before you do so.  ' +
                        'Are you sure you would like to continue?',

    selectNodes: 'Choose which of your projects and components to make public or private. Checked projects and components will be public, unchecked is private.',

    addonWarning: 'The following addons will be effected by this change.',

    nodesPublic: 'The following nodes will be make public',

    nodesPrivate: 'The following nodes will be make public'
};

var URLS = {
    makePublic: window.nodeApiUrl + 'permissions/public/',
    makePrivate: window.nodeApiUrl + 'permissions/private/'
};
var PUBLIC = 'public';
var PRIVATE = 'private';
var PROJECT = 'project';
var COMPONENT = 'component';


function getNodesOriginal(nodeTree, nodesOriginal) {
    var i;
    var nodeId = nodeTree.node.id;
    nodesOriginal[nodeId] = {
        public: nodeTree.node.is_public,
        id: nodeTree.node.id,
        addons: nodeTree.node.addons,
        title: nodeTree.node.title,
        changed: false
    }

    if (nodeTree.children) {
        for (i in nodeTree.children) {
            nodesOriginal = getNodesOriginal(nodeTree.children[i], nodesOriginal);
        }
    }
    //var localNodes = nodesOriginal;
    return nodesOriginal;
}

//function patchNodePrivacy(node) {
//    var url = API_BASE + node.id + '/';
//
//    var msgKey;
//    var isRegistration = window.contextVars.node.isRegistration;
//
//    if (permissions === PUBLIC && isRegistration) { msgKey = 'makeRegistrationPublicWarning'; }
//    else if(permissions === PUBLIC && nodeType === PROJECT) { msgKey = 'makeProjectPublicWarning'; }
//    else if(permissions === PUBLIC && nodeType === COMPONENT) { msgKey = 'makeComponentPublicWarning'; }
//    else if(permissions === PRIVATE && nodeType === PROJECT) { msgKey = 'makeProjectPrivateWarning'; }
//    else { msgKey = 'makeComponentPrivateWarning'; }
//
//    var urlKey = permissions === PUBLIC ? 'makePublic' : 'makePrivate';
//    var buttonText = permissions === PUBLIC ? 'Make Public' : 'Make Private';
//
//    var message = MESSAGES[msgKey];
//
//$.ajax({
//    $osf.postJSON(
//    URLS[urlKey],
//    {permissions: permissions}
//    ).done(function() {
//    window.location.reload();
//    }).fail(
//    osfHelpers.handleJSONError
//);
//}
//
//
//}

function patchNodePrivacy(node) {
    var url = API_BASE + node.id + '/';
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
               'id':   node.id,
               'attributes': {
                   'public': node.public
               }
        }
        })
    }).done(function(response) {
        console.log("response is " + JSON.stringify(response));
        console.log("time is " + JSON.stringify(Date.now()));
    }).fail(function(xhr, status, error) {
        //$privacysMsg.addClass('text-danger');
        //$privacysMsg.text('Could not retrieve project settings.');
        Raven.captureMessage('Could not PATCH project settings.', {
            url: url,  status: status, error: error
        });
    });

}

var NodesPrivacyViewModel = function(data) {
    var self = this;
    var nodesOriginal = {};

    self.nodesState = ko.observableArray();

    self.nodesState.subscribe(function(newValue) {
        console.log('nodesState is ' + JSON.stringify(newValue));
        m.redraw(true);
    });

    self.nodeParent = ko.observable();
    //Parent node is public or not


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
        nodesOriginal = getNodesOriginal(response[0], nodesOriginal);
        self.nodesState(nodesOriginal);
        new NodesPrivacyTreebeard(response, self.nodesState, nodesOriginal);
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
        for (var node in nodesState) {
            if (nodesState[node].changed) {
                patchNodePrivacy(nodesState[node]);
            }
        }
        window.location.reload();
    };

    self.clear = function() {
        self.page('warning');
        self.nodesState(nodesOriginal);
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
    _NodesPrivacyViewModel: NodesPrivacyViewModel,
    NodesPrivacy: NodesPrivacy
};
