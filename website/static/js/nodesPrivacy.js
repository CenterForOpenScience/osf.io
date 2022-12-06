/**
 * Controller for changing privacy settings for a node and its children.
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('./osfHelpers');
var osfHelpers = require('js/osfHelpers');
var m = require('mithril');
var NodesPrivacyTreebeard = require('js/nodesPrivacySettingsTreebeard');

var MESSAGES = {
    makeProjectPublicWarning:
    'Please review your projects, components, and add-ons for sensitive or restricted information before making them public.' +
    '<br><br>Once they are made public, you should assume they will always be public. You can ' +
        'return them to private later, but search engines (including Google’s cache) or others may access files, wiki pages, or analytics before you do.',
    makeProjectPrivateWarning:
    '<ul><li>Public forks and registrations of this project will remain public.</li>' +
    '<li>Search engines (including Google\'s cache) or others may have accessed files, wiki pages, or analytics while this project was public.</li></ul>' +
    '<li>The project will automatically be removed from any collections, and will need to be resubmitted to the collection in the future.</li></ul>',
    makeSupplementalProjectPrivateWarning:
    '<ul><li>Preprints will remain public.</li><li>Public forks and registrations of this project will remain public.</li>' +
    '<li>Search engines (including Google\'s cache) or others may have accessed files, wiki pages, or analytics while this project was public.</li></ul>',
    makeEmbargoPublicWarning: 'By clicking confirm, an email will be sent to project administrator(s) to approve ending the embargo. If approved, this registration, including any components, will be made public immediately. This action is irreversible.',
    makeEmbargoPublicTitle: 'End embargo early',
    selectNodes: 'Adjust your privacy settings by checking the boxes below. ' +
    '<br><br><b>Checked</b> projects and components will be <b>public</b>.  <br><b>Unchecked</b> components will be <b>private</b>.',
    confirmWarning: {
        nodesPublic: 'The following projects and components will be made <b>public</b>.',
        nodesPrivate: 'The following projects and components will be made <b>private</b>.',
        nodesNotChangedWarning: 'No privacy settings were changed. Go back to make a change.',
        tooManyNodesWarning: 'You can only change the privacy of 100 projects and components at a time.  Please go back and limit your selection.',
    },
    preprintPrivateWarning: 'This project/component contains supplemental materials for a preprint.'  +
        '<p><strong>Making this project/component private will prevent others from accessing it.</strong></p>'

};

function _flattenNodeTree(nodeTree) {
    var ret = [];
    var stack = [nodeTree];
    while (stack.length) {
        var node = stack.pop();
        ret.push(node);
        stack = stack.concat(node.children);
    }
    return ret;
}

/**
 * take treebeard tree structure of nodes and get a dictionary of parent node and all its
 * children
 */
function getNodesOriginal(nodeTree, nodesOriginal) {
    var flatNodes = _flattenNodeTree(nodeTree);
    $.each(flatNodes, function(_, nodeMeta) {
        nodesOriginal[nodeMeta.node.id] = {
            public: nodeMeta.node.is_public,
            id: nodeMeta.node.id,
            title: nodeMeta.node.title,
            isAdmin: nodeMeta.node.is_admin,
            changed: false,
            isSupplementalProject: nodeMeta.node.is_supplemental_project,
        };
    });
    nodesOriginal[nodeTree.node.id].isRoot = true;
    return nodesOriginal;
}

/**
 * patches all the nodes in a changed state
 * uses API v2 bulk requests
 */
function patchNodesPrivacy(nodes, type) {
    var nodesV2Url = window.contextVars.apiV2Prefix + type + '/';
    var nodesPatch = $.map(nodes, function (node) {
        return {
            'type': type,
            'id': node.id,
            'attributes': {
                'public': node.public
            }
        };
    });
    return $osf.ajaxJSON('PATCH', nodesV2Url, {
        data: {
            data: nodesPatch,
        },
        isCors: true,
        fields: {
            processData: false,
            contentType: 'application/vnd.api+json; ext=bulk',
        }
    });
}

/**
 * view model which corresponds to nodes_privacy.mako (#nodesPrivacy)
 *
 * @type {NodesPrivacyViewModel}
 */
var NodesPrivacyViewModel = function(node, onSetPrivacy) {
    var self = this;
    self.WARNING = 'warning';
    self.SELECT = 'select';
    self.CONFIRM = 'confirm';

    self.onSetPrivacy = onSetPrivacy;

    self.parentIsEmbargoed = node.is_embargoed;
    self.parentIsPublic = node.is_public;
    self.parentNodeType = node.node_type;
    self.isSupplementalProject = node.is_supplemental_project;
    self.dataType = node.is_registration ? 'registrations' : 'nodes';
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
            warning: self.parentIsPublic ?
                'Make ' + self.parentNodeType + ' private' :
                'Warning',
            select: 'Change privacy settings',
            confirm: 'Projects and components affected'
        }[self.page()];
    });

    self.message = ko.computed(function() {
        if (self.page() === self.WARNING && self.parentIsEmbargoed) {
            return MESSAGES.makeEmbargoPublicWarning;
        }

        if (self.page() === self.WARNING && self.isSupplementalProject && self.parentIsPublic) {
              return MESSAGES.preprintPrivateWarning + MESSAGES.makeSupplementalProjectPrivateWarning;
        }

        return {
            warning: self.parentIsPublic ?
                MESSAGES.makeProjectPrivateWarning :
                MESSAGES.makeProjectPublicWarning,
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
            extra: {
                url: self.treebeardUrl, status: status, error: error
            }
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
        patchNodesPrivacy(nodesChanged, self.dataType).then(function () {
            self.onSetPrivacy(nodesChanged);

            self.nodesChangedPublic([]);
            self.nodesChangedPrivate([]);
            self.page(self.WARNING);
            window.location.reload();
        }).fail(function (xhr) {
            $osf.unblock();
            var errorMessage = 'Unable to update project privacy';
            if (xhr.responseJSON && xhr.responseJSON.errors) {
                errorMessage = xhr.responseJSON.errors[0].detail;
            }
            $osf.growl('Problem changing privacy', errorMessage);
            Raven.captureMessage('Could not PATCH project settings.');
            self.clear();
            $('#nodesPrivacy').modal('hide');
        }).always(function() {
            $osf.unblock();
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
        if (nodesState[node].isAdmin) {
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
        if (nodesState[node].isAdmin) {
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

    var nodesChanged = $.map(self.nodesOriginal, function(node) {
	if (node.isRoot) {
            node.public = true;
	    return node;
	}
	return null;
    }).filter(Boolean);
    $osf.block('Submitting request to end embargo early ...');
    patchNodesPrivacy(nodesChanged, self.dataType).then(function (res) {
        $osf.unblock();
        $('.modal').modal('hide');
        self.onSetPrivacy(nodesChanged, true);
        $osf.growl(
            'Email sent',
            'The administrator(s) can approve or cancel the action within 48 hours. If 48 hours pass without any action taken, then the registration will become public.',
            'success'
        );
    });
};

function NodesPrivacy (selector, node, onSetPrivacy) {
    var self = this;

    self.selector = selector;
    self.$element = $(self.selector);
    self.viewModel = new NodesPrivacyViewModel(node, onSetPrivacy);
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
