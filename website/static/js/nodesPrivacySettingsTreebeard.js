'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');


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

function NodesPrivacyTreebeard(divID, data, nodesState, nodesOriginal) {
    /**
     * nodesChanged and nodesState are knockout variables.  nodesChanged will keep track of the nodes that have
     *  changed state.  nodeState is all the nodes in their current state.
     * */
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: divID,
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
            var tb = this;
            var columns = [];
            var id = item.data.node.id;
            var nodesStateLocal = ko.toJS(nodesState());
            columns.push(
                {
                    data : 'action',
                    sortInclude : false,
                    filter : false,
                    custom : function () {
                        return m('input[type=checkbox]', {
                            disabled : !item.data.node.can_write,
                            onclick : function() {
                                item.data.node.is_public = !item.data.node.is_public;
                                item.open = true;
                                nodesStateLocal[id].public = item.data.node.is_public;
                                if (nodesStateLocal[id].public !== nodesOriginal[id].local) {
                                    nodesStateLocal[id].changed = true;
                                }
                                else {
                                    nodesStateLocal[id].changed = false;
                                }
                                nodesState(nodesStateLocal);
                                tb.updateFolder(null, item);
                            },
                            checked: nodesState()[id].public
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

