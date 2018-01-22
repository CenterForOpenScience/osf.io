/**
 * Controller for deleting a node and its children (if they exist)
 */
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('./osfHelpers');
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

function deleteNode(nodeType, isPreprint, nodeApiUrl){
    var preprintMessage = '<br><br>This ' + nodeType + ' contains a <strong>preprint</strong>. Deleting this ' +
      nodeType + ' will also delete your <strong>preprint</strong>. This action is irreversible.';

    // It's possible that the XHR request for contributors has not finished before getting to this
    // point; only construct the HTML for the list of contributors if the contribs list is populated
    var message = '<p>It will no longer be available to other contributors on the project.' +
    (isPreprint ? preprintMessage : '');

    $osf.confirmDangerousAction({
        title: 'Are you sure you want to delete this ' + nodeType + '?',
        message: message,
        callback: function () {
            var request = $.ajax({
                type: 'DELETE',
                dataType: 'json',
                url: nodeApiUrl
            });
            request.done(function(response) {
                // Redirect to either the parent project or the dashboard
                window.location.href = response.url;
            });
            request.fail($osf.handleJSONError);
        },
        buttons: {
            success: {
                label: 'Delete'
            }
        }
    });
}

/**
 * Deletes all nodes in changed state
 * uses API v2 bulk requests
 */
function batchNodesDelete(nodes, nodeType) {
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
        success: function(response){
            if (nodeType === 'project')
                bootbox.alert({
                    message: 'Project has been successfully deleted.',
                    callback: function(confirmed) {
                        window.location.href = '/dashboard/';
                    }
                });

            if (nodeType === 'component')
                bootbox.alert({
                    message: 'Component has been successfully deleted.',
                    callback: function(confirmed) {
                        window.location = window.contextVars.node.parentUrl || window.contextVars.node.urls.web;
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
var NodesDeleteViewModel = function(nodeType, isPreprint, nodeApiUrl) {
    var self = this;

    self.SELECT = 'select';
    self.CONFIRM = 'confirm';
    self.QUICKDELETE = 'quickDelete';
    self.nodeType = nodeType;
    self.confirmationString = '';
    self.treebeardUrl = nodeApiUrl + 'tree/';
    self.isPreprint = isPreprint;
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
        var message = 'It looks like your ' + self.nodeType + ' has components within it. To delete this ' +
          self.nodeType + ', you must also delete all child components.';

        var preprintMessage = '<br><br>This ' + self.nodeType + ' also contains a <strong>preprint</strong>. Deleting this ' +
          self.nodeType + ' will also delete your <strong>preprint</strong>. This action is irreversible.';

        var confirm_message = 'The following ' + (self.nodeType === 'project' ? 'project and ' : '') + 'components will be deleted.';

        if (self.page() === self.CONFIRM) {
            return confirm_message;
        }

        return {
            select: message + (self.isPreprint ? preprintMessage : ''),
            confirm: confirm_message
        }[self.page()];
    });

    self.warning = ko.computed(function() {
        return 'Please note that deleting your ' + self.nodeType + ' will erase all your ' +
          self.nodeType + ' data and this process is IRREVERSIBLE.';
    });
    self.atMaxLength = ko.observable(false);
    self.confirmInput = ko.observable('');
    self.canDelete = ko.observable(false);
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

NodesDeleteViewModel.prototype.handleEditableUpdate = function(element) {
    var self = this;
    var $element = $(element);
    var inputText = $element[0].innerText;
    var inputTextLength = inputText.length;

    self.atMaxLength(inputTextLength >= self.confirmationString.length);
    self.canDelete(inputText === self.confirmationString);
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

    if (nodesChanged.length <= 100) {
        $osf.block('Deleting Project');
        batchNodesDelete(nodesChanged.reverse(), self.nodeType).then(function () {
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
};

NodesDeleteViewModel.prototype.clear = function() {
    this.nodesChanged([]);
    this.page(this.SELECT);
};

NodesDeleteViewModel.prototype.back = function() {
    this.nodesChanged([]);
    this.page(this.SELECT);
};

/**
 * view model which corresponds to nodes_delete.mako (#nodesDelete)
 * Used for quickly deleting nodes with no children.
 * @type {QuickDeleteViewModel}
 */

var QuickDeleteViewModel = function(nodeType, isPreprint, nodeApiUrl){
    var self = this;
    self.confirmationString = $osf.getConfirmationString();
    self.QUICKDELETE = 'quickDelete';
    self.SELECT = 'select';
    self.CONFIRM = 'confirm';
    self.page = ko.observable(self.QUICKDELETE);
    self.confirmInput = ko.observable('');
    self.canDelete = ko.observable(false);
    self.nodeType = nodeType;
    self.nodeApiUrl = nodeApiUrl;
    self.isPreprint = isPreprint;
    self.message = ko.computed(function(){
        var preprintMessage = '<br><br>This ' + self.nodeType + ' contains a <strong>preprint</strong>. Deleting this ' +
          self.nodeType + ' will also delete your <strong>preprint</strong>. This action is irreversible.';
        var message = 'It will no longer be available to other contributors on the project.' +
        (self.isPreprint ? preprintMessage : '');

        return message;
    });
    self.atMaxLength = ko.observable(false);
    self.nodesDeleted = ko.observable(true);
    self.pageTitle = ko.computed(function() {
        return 'Are you sure you want to delete this ' + self.nodeType + '?';
    });
};

QuickDeleteViewModel.prototype.clear = function(){
    var self = this;
    self.nodesDeleted = ko.observable(false);
};

QuickDeleteViewModel.prototype.handleEditableUpdate = function(element) {
    var self = this;
    var $element = $(element);
    var inputText = $element[0].innerText;
    var inputTextLength = inputText.length;

    self.atMaxLength(inputTextLength >= self.confirmationString.length);
    self.canDelete(inputText === self.confirmationString);
};

QuickDeleteViewModel.prototype.confirmChanges = function(){
    var self = this;
    var request = $.ajax({
        type: 'DELETE',
        dataType: 'json',
        url: self.nodeApiUrl
    });
    request.done(function(response) {
        // Redirect to either the parent project or the dashboard
        window.location.href = response.url;
    });
    request.fail($osf.handleJSONError);
};

function NodesDelete(childExists, nodeType, isPreprint, nodeApiUrl) {
    var self = this;

    self.selector = '#nodesDelete';
    self.$element = $(self.selector);

    if (childExists) {
        self.viewModel = new NodesDeleteViewModel(nodeType, isPreprint, nodeApiUrl);
        self.viewModel.fetchNodeTree().done(function(response) {
            new NodesDeleteTreebeard('nodesDeleteTreebeard', response, self.viewModel.nodesState, self.viewModel.nodesOriginal);
        });
    } else {
        self.viewModel = new QuickDeleteViewModel(nodeType, isPreprint, nodeApiUrl);
    }

    return self.viewModel;
}

var NodesDeleteManager = function(){
    var self = this;

    self.modal = ko.observable();
    self.delete = function (childExists, nodeType, isPreprint, nodeApiUrl) {
        return self.modal(new NodesDelete(childExists, nodeType, isPreprint, nodeApiUrl));
    };
};

var DeleteManager = function(selector){
    var self = this;

    self.selector = selector;
    self.$element = $(self.selector)[0];
    self.viewModel = new NodesDeleteManager();
    $osf.applyBindings(self.viewModel, self.selector);
};

module.exports = {
    _NodesDeleteViewModel: NodesDeleteViewModel,
    DeleteManager: DeleteManager
};
