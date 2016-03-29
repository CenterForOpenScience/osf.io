/**
 * Controller for changing privacy settings for a node and its children.
 */
'use strict';

var $ = require('jquery');
var $3 = window.$3;
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('./osfHelpers');
var osfHelpers = require('js/osfHelpers');
var m = require('mithril');
var Treebeard = require('treebeard');
var NodesPrivacyTreebeard = require('js/nodesPrivacySettingsTreebeard');

var MESSAGES = {
    makeProjectPublicWarning:
    'Please review your projects, components, and add-ons for sensitive or restricted information before making them public.' +
    '<br><br>Once they are made public, you should assume they will always be public. You can ' +
        'return them to private later, but search engines (including Google’s cache) or others may access files before you do.',
    makeEmbargoPublicWarning: 'By making this registration public, you will end the embargo period and the registration will be open to the public. Making this registration public will automatically make all of its components public as well. This action is irreversible.',
    makeEmbargoPublicTitle: 'End Embargo Early',
    selectNodes: 'Adjust your privacy settings by checking the boxes below. ' +
    '<br><br><b>Checked</b> projects and components will be <b>public</b>.  <br><b>Unchecked</b> components will be <b>private</b>.',
    confirmWarning: {
        nodesPublic: 'The following projects and components will be made <b>public</b>.',
        nodesPrivate: 'The following projects and components will be made <b>private</b>.',
        nodesNotChangedWarning: 'No privacy settings were changed. Go back to make a change.',
        tooManyNodesWarning: 'You can only change the privacy of 100 projects and components at a time.  Please go back and limit your selection.'
    }
};

/**
 * take treebeard tree structure of nodes and get a dictionary of parent node and all its
 * children
 */
function getNodesOriginal(nodeTree, nodesOriginal) {
    var i;
    var nodeId = nodeTree.node.id;
    nodesOriginal[nodeId] = {
        public: nodeTree.node.is_public,
        id: nodeTree.node.id,
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

/**
 * patches all the nodes in a changed state
 * uses API v2 bulk requests
 */
function patchNodesPrivacy(nodes) {
    var nodesV2Url = window.contextVars.apiV2Prefix + 'nodes/';
    var nodesPatch = $.map(nodes, function (node) {
        return {
            'type': 'nodes',
            'id': node.id,
            'attributes': {
                'public': node.public
            }
        };
    });
    //s3 is a very recent version of jQuery that fixes a known bug when used in internet explorer
    return $3.ajax({
        url: nodesV2Url,
        type: 'PATCH',
        dataType: 'json',
        contentType: 'application/vnd.api+json; ext=bulk',
        crossOrigin: true,
        xhrFields: {withCredentials: true},
        processData: false,
        data: JSON.stringify({
            data: nodesPatch
        })
    });
}

/**
 * view model which corresponds to nodes_privacy.mako (#nodesPrivacy)
 *
 * @type {NodesPrivacyViewModel}
 */
var NodesPrivacyViewModel = function(node) {
    var self = this;
    self.WARNING = 'warning';
    self.SELECT = 'select';
    self.CONFIRM = 'confirm';

    self.parentIsEmbargoed = node.is_embargoed;
    self.parentIsPublic = node.is_public;
    self.treebeardUrl = window.contextVars.node.urls.api  + 'tree/';
    self.nodesOriginal = {};
    self.nodesChanged = ko.observable();
    //state of current nodes
    self.nodesState = ko.observableArray();
    self.nodesState.subscribe(function(newValue) {
        var nodesChanged = 0;
        for (var key in newValue) {
            if (newValue[key].public !== self.nodesOriginal[key].public) {
                newValue[key].changed = true;
                nodesChanged++;
            }
            else {
                newValue[key].changed = false;
            }
        }
        self.nodesChanged(nodesChanged > 0);
        m.redraw(true);
    });
    //original node state on page load
    self.nodesChangedPublic = ko.observableArray([]);
    self.nodesChangedPrivate = ko.observableArray([]);
    self.hasChildren = ko.observable(false);
    $('#nodesPrivacy').on('hidden.bs.modal', function () {
        self.clear();
    });

    self.page = ko.observable(self.WARNING);

    self.pageTitle = ko.computed(function() {
        if (self.page() === self.WARNING &&  self.parentIsEmbargoed) {
            return MESSAGES.makeEmbargoPublicTitle;
        }


        return {
            warning: 'Warning',
            select: 'Change privacy settings',
            confirm: 'Projects and components affected'
        }[self.page()];
    });

    self.message = ko.computed(function() {
        if (self.page() === self.WARNING &&  self.parentIsEmbargoed) {
            return MESSAGES.makeEmbargoPublicWarning;
        }

        return {
            warning: MESSAGES.makeProjectPublicWarning,
            select: MESSAGES.selectNodes,
            confirm: MESSAGES.confirmWarning
        }[self.page()];
    });
};

/**
 * get node tree for treebeard from API V1
 */
NodesPrivacyViewModel.prototype.fetchNodeTree = function() {
    var self = this;

    return $.ajax({
        url: self.treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        self.nodesOriginal = getNodesOriginal(response[0], self.nodesOriginal);
        var size = 0;
        $.each(Object.keys(self.nodesOriginal), function(_, key) {
            if (self.nodesOriginal.hasOwnProperty(key)) {
                size++;
            }
        });
        self.hasChildren(size > 1);
        var nodesState = $.extend(true, {}, self.nodesOriginal);
        var nodeParent = response[0].node.id;
        //change node state and response to reflect button push by user on project page (make public | make private)
        nodesState[nodeParent].public = response[0].node.is_public = !self.parentIsPublic;
        nodesState[nodeParent].changed = true;
        self.nodesState(nodesState);
    }).fail(function(xhr, status, error) {
        $osf.growl('Error', 'Unable to retrieve project settings');
        Raven.captureMessage('Could not GET project settings.', {
            url: self.treebeardUrl, status: status, error: error
        });
    });
};

NodesPrivacyViewModel.prototype.selectProjects = function() {
    this.page(this.SELECT);
};

NodesPrivacyViewModel.prototype.confirmWarning =  function() {
    var nodesState = ko.toJS(this.nodesState);
    for (var node in nodesState) {
        if (nodesState[node].changed) {
            if (nodesState[node].public) {
                this.nodesChangedPublic().push(nodesState[node].title);
            }
            else {
                this.nodesChangedPrivate().push(nodesState[node].title);
            }
        }
    }
    this.page(this.CONFIRM);
};

NodesPrivacyViewModel.prototype.confirmChanges =  function() {
    var self = this;

    var nodesState = ko.toJS(this.nodesState());
    nodesState = Object.keys(nodesState).map(function(key) {
        return nodesState[key];
    });
    var nodesChanged = nodesState.filter(function(node) {
        return node.changed;
    });
    //The API's bulk limit is 100 nodes.  We catch the exception in nodes_privacy.mako.
    if (nodesChanged.length <= 100) {
        $osf.block('Updating Privacy');
        patchNodesPrivacy(nodesChanged).then(function () {
            $osf.unblock();
            self.nodesChangedPublic([]);
            self.nodesChangedPrivate([]);
            self.page(self.WARNING);
            window.location.reload();
        }).fail(function () {
            $osf.unblock();
            $osf.growl('Error', 'Unable to update project privacy');
            Raven.captureMessage('Could not PATCH project settings.');
            self.clear();
            window.location.reload();
        });
    }
};

NodesPrivacyViewModel.prototype.clear = function() {
    this.nodesChangedPublic([]);
    this.nodesChangedPrivate([]);
    this.page(this.WARNING);
};

NodesPrivacyViewModel.prototype.selectAll = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        if (nodesState[node].canWrite) {
            nodesState[node].public = true;
            nodesState[node].changed = nodesState[node].public !== this.nodesOriginal[node].public;
        }
    }
    this.nodesState(nodesState);
    m.redraw(true);
};

NodesPrivacyViewModel.prototype.selectNone = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        if (nodesState[node].canWrite) {
            nodesState[node].public = false;
            nodesState[node].changed = nodesState[node].public !== this.nodesOriginal[node].public;

        }
    }
    this.nodesState(nodesState);
    m.redraw(true);
};

NodesPrivacyViewModel.prototype.back = function() {
    this.nodesChangedPublic([]);
    this.nodesChangedPrivate([]);
    this.page(this.SELECT);
};

NodesPrivacyViewModel.prototype.makeEmbargoPublic = function() {
    var self = this;

    $.each(self.nodesOriginal, function(key, node) {
        node.public = true;
    });
    $osf.block('Submitting request to end embargo early ...');
    patchNodesPrivacy(
        $.map(self.nodesOriginal, function(node) {return node;})
    ).then(function (res) {
        $osf.unblock();
        // Non-error response with Nodes still private implies more than one
        // admin in this registration tree, and approval is needed before the
        // embargo is lifted.
        // Non-error response with Nodes made public implies this user is the
        // only admin on the registration tree, and the privacy was changed
        // immediately.
        if (res.data[0].attributes.public) {
            window.location.reload();
        }
        else {
            $osf.growl(
                'Request Initiated',
                'You have initiated a request to end this registration\'s embargo early, and to make it and all of its components public immediately. All adminstrators on this registration have 48 hours to approve or disapprove of this acrion.',
                'success'
            );
        }
    });
};

function NodesPrivacy (selector, node) {
    var self = this;

    self.selector = selector;
    self.$element = $(self.selector);
    self.viewModel = new NodesPrivacyViewModel(node);
    self.viewModel.fetchNodeTree().done(function(response) {
        new NodesPrivacyTreebeard('nodesPrivacyTreebeard', response, self.viewModel.nodesState, self.viewModel.nodesOriginal);
    });
    self.init();

}

NodesPrivacy.prototype.init = function() {
    osfHelpers.applyBindings(this.viewModel, this.selector);
};

module.exports = {
    _NodesPrivacyViewModel: NodesPrivacyViewModel,
    NodesPrivacy: NodesPrivacy
};
