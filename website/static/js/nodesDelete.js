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

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var BULK_DELETE_LIMIT = 100;

/**
 * view model which corresponds to nodes_delete.mako (#nodesDelete)
 * Used for quickly deleting nodes with no children.
 * @type {QuickDeleteViewModel}
 */

var QuickDeleteViewModel = function (nodeType, isSupplementalProject, nodeApiUrl) {
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
    self.isSupplementalProject = isSupplementalProject;
    self.preprintMessage = sprintf(_('This %1$s also contains supplemental materials for a <strong>preprint</strong>.  It will'),self.nodeType) +
     _(' no longer be available to contributors or connected to the preprint.');

    self.message = ko.computed(function () {
        return (self.isSupplementalProject ? self.preprintMessage :
            _('It will no longer be available to other contributors on the project.'));

    });
    self.atMaxLength = ko.observable(false);
    self.nodesDeleted = ko.observable(true);
    self.pageTitle = ko.computed(function () {
        return sprintf(_('Are you sure you want to delete this %1$s?'),_(self.nodeType));
    });
};

QuickDeleteViewModel.prototype.clear = function () {
    var self = this;
    self.nodesDeleted = ko.observable(false);
};

QuickDeleteViewModel.prototype.handleEditableUpdate = function (element) {
    var self = this;
    var $element = $(element);
    var inputText = $element[0].innerText;
    var inputTextLength = inputText.length;

    self.atMaxLength(inputTextLength >= self.confirmationString.length);
    self.canDelete(inputText === self.confirmationString);
};

QuickDeleteViewModel.prototype.confirmChanges = function () {
    var self = this;
    var request = $.ajax({
        type: 'DELETE',
        dataType: 'json',
        url: self.nodeApiUrl
    });
    request.done(function (response) {
        // Redirect to either the parent project or the dashboard
        window.location.href = response.url;
    });
    request.fail( function (xhr, status, error) {
        var errorMessage = sprintf(_('Unable to delete %1$s') , self.nodeType);
        if (xhr.responseJSON && xhr.responseJSON.errors) {
            errorMessage = xhr.responseJSON.errors[0].detail;
        }
        $osf.growl(sprintf(_('Problem deleting %1$s') , self.nodeType, errorMessage));
        Raven.captureMessage(sprintf(_('Could not delete %$1s') , self.nodeType), {
            extra: {
                url: self.nodeApiUrl, status: status, error: error
            }
        });
    });
};

/**
 * view model which corresponds to nodes_delete.mako (#nodesDelete)
 * Used for deleting nodes with children.
 * @type {NodesDeleteViewModel}
 */

var NodesDeleteViewModel = function (nodeType, isSupplementalProject, nodeApiUrl) {
    var self = this;
    QuickDeleteViewModel.call(self, nodeType, isSupplementalProject, nodeApiUrl);

    self.confirmationString = '';
    self.tbCache = null;
    self.treebeardUrl = nodeApiUrl + 'tree/';
    self.nodesOriginal = {};
    self.nodesDeleted = ko.observable();
    self.nodesChanged = ko.observableArray([]);
    self.termForChildren = ko.pureComputed(function() {
        return self.nodeType === 'project' ? 'components' : 'subcomponents';
    });
    self.nodesState = ko.observableArray();
    self.hasSupplementalProjects = ko.observable(false);
    self.preprintMessage = ko.computed(function() {
        if (self.isSupplementalProject && self.hasSupplementalProjects()) {
            return sprintf(_('<br><br>This %1$s also contains supplemental materials for a <strong>preprint</strong>, and one or more of its %2$s contains supplemental materials for a <strong>preprint</strong>.'),self.nodeType,self.termForChildren());
        }
         if (self.isSupplementalProject && !self.hasSupplementalProjects()) {
            return sprintf(_('<br><br>This %1$s also contains supplemental materials for a <strong>preprint</strong>.'),self.nodeType);
        }
         if (!self.isSupplementalProject && self.hasSupplementalProjects()) {
            return sprintf(_('<br><br>This %1$s also has one or more %2$s that contain supplemental materials for a <strong>preprint</strong>.'),self.nodeType,self.termForChildren());
        }
    });

    self.nodesState.subscribe(function (newValue) {
        var nodesDeleted = 0;
        for (var key in newValue) {
            if (newValue[key].changed !== self.nodesOriginal[key].changed) {
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

    self.pageTitle = ko.computed(function () {
        return {
            select: sprintf(_('Delete %1$s') , self.nodeType),
            confirm: sprintf(_('Delete %1$s and %2$s') ,self.nodeType,self.termForChildren())
        }[self.page()];
    });

    self.message = ko.computed(function () {
        var message = sprintf(_('This %1$s contains %2$s.') ,self.nodeType,self.termForChildren()) + sprintf(_(' To delete this %1$s, you must also delete all %2$s.') ,self.nodeType,self.termForChildren());

        var confirm_message = sprintf(_(' The following %1$s and %2$s will be deleted.'),self.nodeType,self.termForChildren());

        return {
            select: message + ((self.isSupplementalProject || self.hasSupplementalProjects()) ? self.preprintMessage() : _(' This action is irreversible.')),
            confirm: confirm_message
        }[self.page()];
    });

    self.warning = ko.computed(function () {
        var message = sprintf(_('Please note that deleting your %1$s will erase all your %2$s data and this process is IRREVERSIBLE. Deleted %3$s and %4$s will no longer be available to other contributors on the %5$s') ,self.nodeType,self.nodeType,self.nodeType,self.termForChildren(),self.nodeType);
        return self.hasSupplementalProjects() ? message + _(' and will be disconnected from your preprints.') : message + _('.');
    });
};

NodesDeleteViewModel.prototype = Object.create(QuickDeleteViewModel.prototype);

NodesDeleteViewModel.prototype.fetchNodeTree = function () {
    var self = this;

    return $.ajax({
        url: self.treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function (response) {
        getNodesOriginal.call(self, response[0]);
        var size = 0;
        $.each(Object.keys(self.nodesOriginal), function (_, key) {
            if (self.nodesOriginal.hasOwnProperty(key)) {
                size++;
            }
        });
        self.hasChildren(size > 1);
        var nodesState = $.extend(true, {}, self.nodesOriginal);
        var nodeParent = response[0].node.id;
        self.nodesState(nodesState);
    }).fail(function (xhr, status, error) {
        $osf.growl('Error', _('Unable to retrieve project settings'));
        Raven.captureMessage(_('Could not GET project settings.'), {
            extra: {
                url: self.treebeardUrl, status: status, error: error
            }
        });
    });
};

NodesDeleteViewModel.prototype.selectProjects = function () {
    var self = this;
    self.page(this.SELECT);
};

NodesDeleteViewModel.prototype.confirmWarning =  function () {
    var self = this;
    var nodesState = ko.toJS(self.nodesState);
    for (var node in nodesState) {
        if (nodesState[node].changed) {
            self.nodesChanged().push(nodesState[node].title);
        }
    }
    self.confirmationString = $osf.getConfirmationString();
    self.page(this.CONFIRM);
};

NodesDeleteViewModel.prototype.selectAll = function () {
    var self = this;

    var nodesState = ko.toJS(self.nodesState());
    for (var node in nodesState) {
        if (nodesState[node].isAdmin) {
            nodesState[node].changed = true;
        }
    }
    self.nodesState(nodesState);
    m.redraw(true);
};

NodesDeleteViewModel.prototype.confirmChanges =  function () {
    var self = this;

    var nodesState = ko.toJS(this.nodesState());
    nodesState = Object.keys(nodesState).map(function (key) {
        return nodesState[key];
    });
    var nodesChanged = nodesState.filter(function (node) {
        return node.changed;
    });

    $osf.block('Deleting ' + self.nodeType);
    batchNodesDelete.call(self, nodesChanged.reverse()).always(function () {
        $osf.unblock();
    });
};

NodesDeleteViewModel.prototype.clear = function () {
    var self = this;
    self.nodesChanged([]);
    self.page(self.SELECT);
    self.tbCache = null;
};

NodesDeleteViewModel.prototype.back = function () {
    var self = this;
    self.nodesChanged([]);
    self.page(self.SELECT);
    return new NodesDeleteTreebeard('nodesDeleteTreebeard', self.tbCache, self.nodesState, self.nodesOriginal);
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
function getNodesOriginal(nodeTree) {
    var self =this;
    var flatNodes = _flattenNodeTree(nodeTree);
    $.each(flatNodes, function (_, nodeMeta) {
        self.nodesOriginal[nodeMeta.node.id] = {
            id: nodeMeta.node.id,
            title: nodeMeta.node.title,
            isAdmin: nodeMeta.node.is_admin,
            changed: false,
            isSupplementalProject: nodeMeta.node.is_supplemental_project,
        };
        !self.hasSupplementalProjects() &&
          (nodeMeta.node.is_supplemental_project && nodeMeta.node.id !== nodeTree.node.id) &&
            self.hasSupplementalProjects(true);
    });
    self.nodesOriginal[nodeTree.node.id].isRoot = true;
}

/**
 * Deletes all nodes in changed state
 * uses API v2 bulk requests
 */
function batchNodesDelete(nodes) {
    var self = this;
    var nodesV2Url = window.contextVars.apiV2Prefix + 'nodes/';
    var size = BULK_DELETE_LIMIT;
    var batches = [];

    while (nodes.length) {
        batches.push($.map(nodes.splice(0, size), function (node) {
            return {
                'type': 'nodes',
                'id': node.id,
            };
        }));
    }

    var requests = $.map(batches, function (batch) {
        return $osf.ajaxJSON('DELETE', nodesV2Url, {
            data: {
                data: batch
            },
            isCors: true,
            fields: {
                contentType: 'application/vnd.api+json; ext=bulk',
                processData: false
            }
        });
    });

    return $.when.apply($, requests).then(function (_) {
            bootbox.alert({
                message: sprintf(_('Your %1$s has been successfully deleted.'),self.nodeType),
                callback: function (confirmed) {
                    window.location = self.nodeType === 'project' ?
                      '/dashboard/' :
                      window.contextVars.node.parentUrl || window.contextVars.node.urls.web;
                }
            });
        }, function (xhr) {
            $osf.unblock();
            var errorMessage = sprintf(_('Unable to delete %1$s') , self.nodeType);
            if (xhr.responseJSON && xhr.responseJSON.errors) {
                errorMessage = xhr.responseJSON.errors[0].detail;
            }
            $osf.growl(sprintf(_('Problem deleting %1$s') , self.nodeType), errorMessage);
            Raven.captureMessage(_('Could not batch delete project and its components.'));
            self.clear();
            $('#nodesDelete').modal('hide');
        });
}

function NodesDelete(childExists, nodeType, isSupplementalProject, nodeApiUrl) {
    var self = this;

    self.selector = '#nodesDelete';
    self.$element = $(self.selector);

    if (childExists) {
        self.viewModel = new NodesDeleteViewModel(nodeType, isSupplementalProject, nodeApiUrl);
        self.viewModel.fetchNodeTree().done(function (response) {
            self.viewModel.tbCache = response;
            new NodesDeleteTreebeard('nodesDeleteTreebeard', response, self.viewModel.nodesState, self.viewModel.nodesOriginal);
        });
    } else {
        self.viewModel = new QuickDeleteViewModel(nodeType, isSupplementalProject, nodeApiUrl);
    }

    return self.viewModel;
}

var NodesDeleteManager = function () {
    var self = this;

    self.modal = ko.observable();
    self.delete = function (childExists, nodeType, isSupplementalProject, nodeApiUrl) {
        return self.modal(new NodesDelete(childExists, nodeType, isSupplementalProject, nodeApiUrl));
    };
};

var DeleteManager = function (selector) {
    var self = this;

    self.selector = selector;
    self.$element = $(self.selector)[0];
    self.viewModel = new NodesDeleteManager();
    $osf.applyBindings(self.viewModel, self.selector);
};

module.exports = {
    DeleteManager: DeleteManager,
};
