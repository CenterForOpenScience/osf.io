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

function NodeSelectTreebeard(divID, data, nodesState) {
    /**
     *  nodesState is a knockout variable that syncs the mithril checkbox list with information on the view.  The
     *  changed boolean parameter is used to sync the checkbox with changes, the canWrite boolean parameter is used
     *  to disable the checkbox
     * */
    var nodesStateLocal = ko.toJS(nodesState());
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
        resolveRows: function nodeSelectResolveRows(item){
            var tb = this;
            var columns = [];
            var id = item.data.node.id;
            columns.push(
                {
                    data : 'action',
                    sortInclude : false,
                    filter : false,
                    custom : function () {
                        return m('input[type=checkbox]', {
                            disabled : !nodesStateLocal[id].enabled,
                            onclick : function() {
                                item.data.node.checked = !item.data.node.checked;
                                item.open = true;
                                nodesStateLocal[id].checked = !nodesStateLocal[id].checked;
                                tb.updateFolder(null, item);
                            },
                            checked: nodesState()[id].checked
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
                        if (nodesStateLocal[id].enabled) {
                            return m('span', item.data.node.title);
                        }
                        else {
                            return m('span', {class: 'text-muted'}, item.data.node.title);
                        }
                    }
                }
            );
            return columns;
        }
    });
    nodesState(nodesStateLocal);
    var grid = new Treebeard(tbOptions);
    expandOnLoad.call(grid.tbController);
}
module.exports = NodeSelectTreebeard;

