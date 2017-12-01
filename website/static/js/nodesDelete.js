/**
 * Controller for deleting a node and it childs (if they exists)
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('./osfHelpers');
var osfHelpers = require('js/osfHelpers');
var m = require('mithril');
var bootbox = require('bootbox');
var NodesDeleteTreebeard = require('js/nodesDeleteTreebeard');

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
            id: nodeMeta.node.id,
            title: nodeMeta.node.title,
            isAdmin: nodeMeta.node.is_admin,
            changed: false
        };
    });
    nodesOriginal[nodeTree.node.id].isRoot = true;
    return nodesOriginal;
}

/**
 * Deletes all nodes in changed state
 * uses API v2 bulk requests
 */
function batchNodesDelete(nodes) {
    var nodesV2Url = window.contextVars.apiV2Prefix + 'nodes/';
    var nodesBatch = $.map(nodes, function (node) {
        return {
            'type': 'nodes',
            'id': node.id,
        };
    });

    //s3 is a very recent version of jQuery that fixes a known bug when used in internet explorer
    return $.ajax({
        url: nodesV2Url,
        type: 'DELETE',
        dataType: 'json',
        contentType: 'application/vnd.api+json; ext=bulk',
        crossOrigin: true,
        xhrFields: {withCredentials: true},
        processData: false,
        data: JSON.stringify({
            data: nodesBatch
        }),
        success: function(){
            if (window.contextVars.node.nodeType === 'project')
                bootbox.alert({
                    message: 'Project has been successfully deleted.',
                    callback: function(confirmed) {
                        window.location.href = '/dashboard/';
                    }
                });

            if (window.contextVars.node.nodeType === 'component')
                bootbox.alert({
                    message: 'Component has been successfully deleted.',
                    callback: function(confirmed) {
                        window.location = window.contextVars.node.parentUrl;
                    }
                });
        }
    });
}

/**
 * view model which corresponds to nodes_delete.mako (#nodesDelete)
 *
 * @type {NodesDeleteViewModel}
 */
var NodesDeleteViewModel = function(node) {
    var self = this;
    self.nodeType = window.contextVars.node.nodeType;
    self.parentUrl = window.contextVars.node.parentUrl;
    self.SELECT = 'select';
    self.CONFIRM = 'confirm';

    self.confirmationString = '';
    self.treebeardUrl = window.contextVars.node.urls.api  + 'tree/';
    self.nodesOriginal = {};
    self.nodesDeleted = ko.observable();
    self.nodesChanged = ko.observableArray([]);
    //state of current nodes
    self.nodesState = ko.observableArray();
    self.nodesState.subscribe(function(newValue) {
        var nodesDeleted = 0;
        for (var key in newValue) {
            if (newValue[key].changed !== self.nodesOriginal[key].changed){
                newValue[key].changed = true;
                nodesDeleted++;
            }
            else {
                newValue[key].changed = false;
            }
        }
        self.nodesDeleted(nodesDeleted > 0 && nodesDeleted === Object.keys(self.nodesOriginal).length);
        m.redraw(true);
    });
    //original node state on page load
    self.hasChildren = ko.observable(false);
    $('#nodesDelete').on('hidden.bs.modal', function () {
        self.clear();
    });

    self.page = ko.observable(self.SELECT);

    self.pageTitle = ko.computed(function() {
        if (self.nodeType === 'project'){
            return {
                select: 'Delete Project',
                confirm: 'Delete Project and Components'
            }[self.page()];
        }

        if (self.nodeType === 'component'){
            return {
                select: 'Delete Component',
                confirm: 'Delete Components'
            }[self.page()];
        }

    });

    self.message = ko.computed(function() {
        if (self.page() === self.CONFIRM) {
            if (self.nodeType === 'project')
                return 'The following project and components will be deleted';

            if (self.nodeType === 'component')
                return 'The following components will be deleted';
        }

        if (self.nodeType === 'project')
            return {
                select: 'It looks like your project has components within it. To delete this project, you must also delete all child components',
                confirm: 'The following project and components will be deleted.'
            }[self.page()];

        if (self.nodeType === 'component')
            return {
                select: 'It looks like your componet has components within it. To delete this component, you must also delete all child components',
                confirm: 'The following components will be deleted.'
            }[self.page()];
    });

    self.warning = ko.computed(function() {
        if (self.nodeType === 'project')
            return 'Please note that deleting your project will erase all your project data and this process is IRREVERSIBLE.';

        if (self.nodeType === 'component')
            return 'Please note that deleting your component will erase all your component data and this process is IRREVERSIBLE.';
    });
};

/**
 * get node tree for treebeard from API V1
 */
NodesDeleteViewModel.prototype.fetchNodeTree = function() {
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

NodesDeleteViewModel.prototype.selectProjects = function() {
    this.page(this.SELECT);
};

NodesDeleteViewModel.prototype.confirmWarning =  function() {
    var nodesState = ko.toJS(this.nodesState);
    for (var node in nodesState) {
        if (nodesState[node].changed) {
            this.nodesChanged().push(nodesState[node].title);
        }
    }
    this.confirmationString = $osf.getConfirmationString();
    this.page(this.CONFIRM);
};

NodesDeleteViewModel.prototype.selectAll = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        if (nodesState[node].isAdmin) {
            nodesState[node].changed = true;
        }
    }
    this.nodesState(nodesState);
    m.redraw(true);
};


NodesDeleteViewModel.prototype.confirmChanges =  function() {
    var self = this;

    var nodesState = ko.toJS(this.nodesState());
    nodesState = Object.keys(nodesState).map(function(key) {
        return nodesState[key];
    });
    var nodesChanged = nodesState.filter(function(node) {
        return node.changed;
    });

    if ($('#bbConfirmTextDelete').val() === this.confirmationString) {
        if (nodesChanged.length <= 100) {
            $osf.block('Deleting Project');
            batchNodesDelete(nodesChanged.reverse()).then(function () {
                self.page(self.WARNING);
            }).fail(function (xhr) {
                $osf.unblock();
                var errorMessage = 'Unable to delete project';
                if (xhr.responseJSON && xhr.responseJSON.errors) {
                    errorMessage = xhr.responseJSON.errors[0].detail;
                }
                $osf.growl('Problem deleting project', errorMessage);
                Raven.captureMessage('Could not batch delete projects.');
                self.clear();
                $('#nodesDelete').modal('hide');
            }).always(function() {
                $osf.unblock();
            });
        }
    }
    else {
        $osf.growl('Verification failed', 'Strings did not match');
    }
};

NodesDeleteViewModel.prototype.clear = function() {
    this.nodesChanged([]);
    this.page(this.SELECT);
};

NodesDeleteViewModel.prototype.back = function() {
    this.nodesChanged([]);
    this.page(this.SELECT);
};

function NodesDelete(selector, node) {
    var self = this;

    self.selector = selector;
    self.$element = $(self.selector);
    self.viewModel = new NodesDeleteViewModel(node);
    self.viewModel.fetchNodeTree().done(function(response) {
        new NodesDeleteTreebeard('nodesDeleteTreebeard', response, self.viewModel.nodesState, self.viewModel.nodesOriginal);
    });
    self.init();
}

NodesDelete.prototype.init = function() {
    osfHelpers.applyBindings(this.viewModel, this.selector);
};

module.exports = {
    _NodesDeleteViewModel: NodesDeleteViewModel,
    NodesDelete: NodesDelete
};

