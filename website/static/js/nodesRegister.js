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
var Treebeard = require('treebeard');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');


function NodesRegisterTreebeard(divID, data, nodesState, nodesOriginal) {
    /**
     * nodesChanged and nodesState are knockout variables.  nodesChanged will keep track of the nodes that have
     *  changed state.  nodeState is all the nodes in their current state.
     * */
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: divID,
        filesData: data,
        naturalScrollLimit: 0,
        rowHeight: 35,
        hScroll: 0,
        columnTitles: function () {
            return [
                {
                    title: 'checkBox',
                    width: '4%',
                    sortType: 'text',
                    sort: true
                },
                {
                    title: 'project',
                    width: '96%',
                    sortType: 'text',
                    sort: true
                }
            ];
        },
        ondataload: function () {
            var tb = this;
            expandOnLoad.call(tb);
        },
        resolveRows: function nodesPrivacyResolveRows(item) {
            var tb = this;
            var columns = [];
            var id = item.data.node.id;
            var nodesStateLocal = ko.toJS(nodesState());
            item.data.node.selected = nodesStateLocal[id].selected;
            columns.push(
                {
                    data: 'action',
                    sortInclude: false,
                    filter: false,
                    custom: function () {
                        return m('input[type=checkbox]', {
                            disabled: !item.data.node.is_admin,
                            onclick: function () {
                                item.data.node.selected = !item.data.node.selected;
                                item.open = true;
                                nodesStateLocal[id].selected = item.data.node.selected;
                                if (nodesStateLocal[id].selected !== nodesOriginal[id].local) {
                                    nodesStateLocal[id].changed = true;
                                }
                                else {
                                    nodesStateLocal[id].changed = false;
                                }
                                nodesState(nodesStateLocal);
                                tb.updateFolder(null, item);
                            },
                            checked: nodesState()[id].selected
                        });
                    }
                },
                {
                    data: 'project',  // Data field name
                    folderIcons: true,
                    filter: true,
                    sortInclude: false,
                    hideColumnTitles: false,
                    custom: function () {
                        return m('span', item.data.node.title);
                    }
                }
            );
            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
}

var MESSAGES = {
    selectNodes: 'Select the nodes you want to register.<br><br>Nodes must be have a parent registered or be a top-level node.',
    confirmWarning: {
        nodesRegistered: 'The following projects and components will be registered.',
    },
    preprintPrivateWarning: 'The project you are attempting to make private currently represents a preprint.' +
    '<p><strong>Making this project private will remove this preprint from circulation.</strong></p>'
};

function _flattenNodeTree(nodeTree) {
    var ret = [];
    var stack = [nodeTree];
    while (stack.length) {
        var node = stack.pop();
        if(node.children){
            $.each(node.children, function(_, child){
                child.parent = node.node.id;
            });
            stack = stack.concat(node.children);
        }
        ret.push(node);

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
        console.log(nodeMeta);
        console.log(nodesOriginal);
        nodesOriginal[nodeMeta.node.id] = {
            selected: false,
            id: nodeMeta.node.id,
            title: nodeMeta.node.title,
            isAdmin: nodeMeta.node.is_admin,
            changed: false,
            parent: nodeMeta.node.parent
        };
    });
    nodesOriginal[nodeTree.node.id].isRoot = true;
    return nodesOriginal;
}

/**
 * patches all the nodes in a changed state
 * uses API v2 bulk requests
 */
function patchNodesRegister(nodes, type) {
    var registerV2Url = window.contextVars.apiV2Prefix + '/nodes/' + window.contextVars.node.id  + '/registrations/';
    var payload = {
              'data': [ ],
            'relationships': {
                'draft': {
                    'id':  window.contextVars.draft.id
                    }
        }
    };
    return $.ajax({
        url: nodesV2Url,
        type: 'POST',
        dataType: 'json',
        contentType: 'application/vnd.api+json; ext=bulk',
        crossOrigin: true,
        xhrFields: {withCredentials: true},
        processData: false,
        data: JSON.stringify({
            data: payload
        })
    });
}

/**
 * view model which corresponds to nodes_register.mako (#nodesRegister)
 *
 * @type {NodesRegisterViewModel}
 */
var NodesRegisterViewModel = function(node, onSetPrivacy) {
    var self = this;
    self.SELECT = 'select';
    self.CONFIRM = 'confirm';

    self.onSetPrivacy = onSetPrivacy;

    self.parentIsEmbargoed = node.is_embargoed;
    self.parentIsPublic = node.is_public;
    self.parentNodeType = node.node_type;
    self.isPreprint = node.is_preprint;
    self.dataType = node.is_registration ? 'registrations' : 'nodes';
    self.treebeardUrl = window.contextVars.node.urls.api  + 'tree/';
    self.nodesOriginal = {};
    self.nodesChanged = ko.observable();
    //state of current nodes
    self.nodesState = ko.observableArray();
    self.nodesState.subscribe(function(newValue) {
        var nodesChanged = 0;
        for (var key in newValue) {
            if (newValue[key].selected !== self.nodesOriginal[key].selected) {
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

    self.nodesSelected = ko.computed(function() {
        var selected = [];
        var nodesState = ko.toJS(self.nodesState());
        for (var node in nodesState) {
            if (nodesState[node].selected) {
                selected.push(nodesState[node]);
            }
        }
        return selected;
    });


    //original node state on page load
    self.hasChildren = ko.observable(false);
    $('#nodesRegister').on('hidden.bs.modal', function () {
        self.clear();
    });

    self.page = ko.observable(self.SELECT);

    self.pageTitle = ko.computed(function() {
        return {
            warning: self.parentIsPublic ?
                'Make ' + self.parentNodeType + ' private' :
                'Warning',
            select: 'Register Selected Nodes',
            confirm: 'Projects and components to be registered'
        }[self.page()];
    });

    self.message = ko.computed(function() {
        return {
            warning: null,
            select: MESSAGES.selectNodes,
            confirm: MESSAGES.confirmWarning
        }[self.page()];
    });
};

/**
 * get node tree for treebeard from API V1
 */
NodesRegisterViewModel.prototype.fetchNodeTree = function() {
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
        //nodesState[nodeParent].selected = response[0].node.is_public = !self.parentIsPublic;
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

NodesRegisterViewModel.prototype.selectProjects = function() {
    this.page(this.SELECT);
};

NodesRegisterViewModel.prototype.confirmWarning =  function() {
    this.page(this.CONFIRM);
};

NodesRegisterViewModel.prototype.confirmChanges =  function() {
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
        $osf.block('Updating Registration');
        patchNodesRegister(nodesChanged, self.dataType).then(function () {
            self.onSetPrivacy(nodesChanged);

            self.page(self.SELECT);
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
            $('#nodesRegister').modal('hide');
        }).always(function() {
            $osf.unblock();
        });
    }
};

NodesRegisterViewModel.prototype.clear = function() {
    this.selectNone();
};

NodesRegisterViewModel.prototype.selectAll = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        if (nodesState[node].isAdmin) {
            nodesState[node].selected = true;
            nodesState[node].changed = nodesState[node].selected !== this.nodesOriginal[node].selected;
        }
    }
    this.nodesState(nodesState);
    m.redraw(true);
};

NodesRegisterViewModel.prototype.selectNone = function() {
    var nodesState = ko.toJS(this.nodesState());
    for (var node in nodesState) {
        if (nodesState[node].isAdmin) {
            nodesState[node].selected = false;
            nodesState[node].changed = nodesState[node].selected !== this.nodesOriginal[node].selected;
        }
    }
    this.nodesState(nodesState);
    m.redraw(true);
};

NodesRegisterViewModel.prototype.back = function() {
    this.page(this.SELECT);
};


function NodesRegister (selector, node, onSetPrivacy) {
    var self = this;

    self.selector = selector;
    self.$element = $(self.selector);
    self.viewModel = new NodesRegisterViewModel(node, onSetPrivacy);
    self.viewModel.fetchNodeTree().done(function(response) {
        new NodesRegisterTreebeard('nodesRegisterTreebeard', response, self.viewModel.nodesState, self.viewModel.nodesOriginal);
    });
    self.init();
}

NodesRegister.prototype.init = function() {
    osfHelpers.applyBindings(this.viewModel, this.selector);
};

module.exports = {
    _NodesRegisterViewModel: NodesRegisterViewModel,
    NodesRegister: NodesRegister
};
