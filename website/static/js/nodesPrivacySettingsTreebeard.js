'use strict';

var $ = require('jquery');
var m = require('mithril');
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

