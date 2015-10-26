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

var ctx = window.contextVars;

var NODE_OFFSET = 25;

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
    addonWarning: 'The following addons will be effected by this change.  Are you sure you want to continue?'
};

function getNodePrivacyDirty(nodeTree, nodesOriginal) {
    var i;
    var nodeId = nodeTree.node.id;
    var nodeIsPublic = nodeTree.node.is_public;
    var addons = nodeTree.node.addons;
    nodesOriginal[nodeId] = {
        isPublic: nodeIsPublic,
        addons: addons
    };
    if (nodeTree.children) {
        for (i in nodeTree.children) {
            nodesOriginal = getNodePrivacyDirty(nodeTree.children[i], nodesOriginal);
        }
    }
    //var localNodes = nodesOriginal;
    return nodesOriginal;
}

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

    self.nodesChanged = ko.observable({});

    self.nodesChanged.subscribe(function(newValue) {
        console.log('nodesChanged is ' + JSON.stringify(newValue));
        console.log('nodesOriginal is ' + JSON.stringify(nodesOriginal));
    });

    // Initialize treebeard grid for privacySettings
    var $privacysMsg = $('#configurePrivacyMessage');
    var treebeardUrl = ctx.node.urls.api  + 'get_node_tree/';

    $.ajax({
        url: treebeardUrl,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        response[0].node.is_public = true;
        addons = getAddons(response[0], addons);
        nodesOriginal = getNodePrivacyDirty(response[0], nodesOriginal);
        self.nodesState(nodesOriginal);
        new NodesPrivacyTreebeard(response, self.nodesState, self.nodesChanged, nodesOriginal);
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
            select: '',
            addon: MESSAGES.addonWarning
        }[self.page()];
    });
    self.message = ko.observable(MESSAGES.makeProjectPublicWarning);



    self.selectProjects =  function() {
        self.page('select');
    };

    self.addonWarning =  function() {
        self.page('addon');
    };

    self.confirmChanges =  function() {
         self.page('warning');
    };

    self.clear = function() {
         self.page('warning');
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

function expandOnLoad() {
    var tb = this;  // jshint ignore: line
    for (var i = 0; i < tb.treeData.children.length; i++) {
        var parent = tb.treeData.children[i];
        tb.updateFolder(null, parent);
        expandChildren(tb, parent.children);
    }
}

function expandChildren(tb, children) {
    var openParent = false;
    for (var i = 0; i < children.length; i++) {
        var child = children[i];
        var parent = children[i].parent();
        if (child.children.length > 0) {
            expandChildren(tb, child.children);
        }
    }
    if (openParent) {
        openAncestors(tb, children[0]);
    }
}

function openAncestors (tb, item) {
    var parent = item.parent();
    if(parent && parent.id > 0) {
        tb.updateFolder(null, parent);
        openAncestors(tb, parent);
    }
}

function NodesPrivacyTreebeard(data, nodesState, nodesChanged, nodesOriginal) {
    /** nodesChanged and nodesState are knockout variables.  nodesChanged will keep track of the nodes that have
     *  changed state.  nodeState is all the nodes in their current state.
     *
     *
     *
     *
     * */
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: 'grid',
        filesData: data,
        naturalScrollLimit : 0,
        rowHeight : 35,
        hScroll : 0,
        columnTitles : function() {
            return [
                {
                    title: 'checkBox',
                    width: '4%',
                    sortType : 'text',
                    sort : true
                },
                {
                    title: 'project',
                    width : '96%',
                    sortType : 'text',
                    sort: true
                }
            ];
        },
        resolveRows: function nodesPrivacyResolveRows(item){
            var columns = [];
            var title = item.data.node.id;
            var nodesStateLocal = ko.toJS(nodesState());
            var nodesChangedLocal = ko.toJS(nodesChanged());

            columns.push(
                {
                    data : 'action',
                    sortInclude : false,
                    filter : false,
                    custom : function () {
                        return m('input[type=checkbox]', {
                            onclick : function() {
                                /* nodesChanged is a knockout variable tracking necessary changes */
                                item.data.node.is_public = !item.data.node.is_public;
                                nodesStateLocal[title] = item.data.node.is_public;
                                if (nodesStateLocal[title] !== nodesOriginal[title]) {
                                    nodesChangedLocal[title] = item.data.node.is_public;
                                }
                                else if (typeof (nodesChangedLocal[title])) {
                                    delete nodesChangedLocal[title];
                                }
                                nodesChanged(nodesChangedLocal);
                                nodesState(nodesStateLocal);
                            },
                            checked: nodesState()[title]
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
    expandOnLoad.call(grid.tbController);
}
module.exports = NodesPrivacyTreebeard;


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
