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
        if (child.data.kind === 'event' && child.data.event.notificationType !== 'adopt_parent') {
            openParent = true;
        }
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

function NodesPrivacyTreebeard(data) {

    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: 'grid',
        filesData: data,
        naturalScrollLimit : 0,
        rowHeight : 35,
        hScroll : 0,
        columnTitles : function() {
            return [
                {
                    title: "checkBox",
                    width: "4%",
                    sortType : "text",
                    sort : true
                },
                {
                    title: "project",
                    width : "96%",
                    sortType : "text",
                    sort: true
                }
            ];
        },
        resolveRows: function nodesPrivacyResolveRows(item){
            return [
                {
                    data : 'action',
                    sortInclude : false,
                    filter : false,
                    custom : function () {
                        var that = this;
                        return m('input[type=checkbox]', {onclick : function() {
                            item.data.is_public = true;
                            that.updateFolder(item, data);
                        },
                            checked: item.data.node.is_public});
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
            ];
        }

    });

    var grid = new Treebeard(tbOptions);
    expandOnLoad.call(grid.tbController);
}

module.exports = NodesPrivacyTreebeard;
