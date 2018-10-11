'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Treebeard = require('treebeard');
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

function NodesDeleteTreebeard(divID, data, nodesState, nodesOriginal) {
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
        ondataload : function () {
            var tb = this;
            expandOnLoad.call(tb);
        },
        resolveRows: function nodesDeleteResolveRows(item){
            var tooltips = function(){
                $('[data-toggle="tooltip"]').tooltip();
            };
            var tb = this;
            var columns = [];
            var id = item.data.node.id;
            var nodesStateLocal = ko.toJS(nodesState());
            //this lets treebeard know when changes come from the knockout side (select all or select none)
            item.data.node.changed = nodesStateLocal[id].changed;
            //A wrapper div for tooltips must exist because tooltips does not work on a disabled element
            var tooltipWrapper = item.data.node.is_admin ? 'div' : 'div[data-toggle="tooltip"][title="You must have admin permissions on this component to be able to delete it."][data-placement="right"]';
            columns.push(
                {
                    data : 'action',
                    sortInclude : false,
                    filter : false,
                    custom : function () {
                        return m(tooltipWrapper, {config: tooltips()},
                            [
                                m('input[type=checkbox]', {
                                    disabled : !item.data.node.is_admin,
                                    onclick : function() {
                                        item.open = true;
                                        nodesStateLocal[id].changed = !nodesStateLocal[id].changed;
                                        nodesState(nodesStateLocal);
                                        tb.updateFolder(null, item);
                                    },
                                    checked: nodesState()[id].changed,
                                })
                            ]
                        );
                    }
                },
                {
                    data: 'project',  // Data field name
                    folderIcons: true,
                    filter: true,
                    sortInclude: false,
                    hideColumnTitles: false,
                    custom: function () {
                        return m('span', [
                                  item.data.node.is_supplemental_project ? m('sup', '*') : m('span'),
                                  m('span', item.data.node.title),
                            ]);
                    }
                }
            );
            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
}
module.exports = NodesDeleteTreebeard;
