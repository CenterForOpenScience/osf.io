'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn');
require('../css/fangorn.css');


// TODO: Refactor out shared utility code between this module, folder picker, and fangorn.js
function resolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' ');

    if (item.children.length > 0) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    item.open = true;
    return '';
}

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


function change_permissions(item, permission) {
    var id = item.parent().data.node.id;
    $osf.putJSON(
        build_path(item, permission), {}
    ).done(function(){
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.event.permission = permission;
    }).fail(function() {
        item.notify.update('Could not update settings.', 'notify-danger', 1, 2000);
    });
}

// Helper to build path
function build_path(item, permission) {
    var id = item.parent().data.node.id;
    var pid = id;
    var url = $osf.apiV2Url(id);
    var test = url.slice(url.lastIndexOf('/')+1);
    var permissions_change_path = '/api/v1/project/';
    var middle = '';
    if(id === test){
        middle = pid
    }
    else{
        pid = item.parent().parent().data.node.id;
        middle = pid + '/node/' + id
    }
    permissions_change_path += middle +
        '/wiki/permissions/'+ permission + '/';
    return permissions_change_path;
}

function ProjectWiki(data) {

    //  Treebeard version
    var tbOptions = {
        divID: 'wgrid',
        filesData: data,
        rowHeight : 33,         // user can override or get from .tb-row height
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        resolveIcon : Fangorn.Utils.resolveIconView,
        hideColumnTitles: true,
        columnTitles : function notificationColumnTitles(item, col) {
            return [
                {
                    title: 'Project',
                    width: '60%',
                    sortType : 'text',
                    sort : false
                },
                {
                    title: 'Editing Toggle',
                    width : '40%',
                    sort : false

                }
            ];
        },
        ontogglefolder : function (item){
            var containerHeight = this.select('#tb-tbody').height();
            this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
            this.redraw();
        },
        resolveRows : function notificationResolveRows(item){
            var columns = [];
            var iconcss = '';
            // check if should not get icon
            if(item.children.length < 1 ){
                iconcss = 'tb-no-icon';
            }
            if (item.data.kind === 'heading') {
                if (item.data.children.length === 0) {
                    columns.push({
                        data : 'project',  // Data field name
                        folderIcons : false,
                        filter : true,
                        sortInclude : false,
                        custom : function() {
                            return m('div[style="padding-left:5px"]',
                                        [m ('p', [
                                                m('b', item.data.node.title + ': '),
                                                m('span[class="text-warning"]', ' No configured projects.')]
                                        )]
                            );
                        }
                    });
                } else {
                    columns.push({
                        data : 'project',  // Data field name
                        folderIcons : false,
                        filter : true,
                        sortInclude : false,
                        custom : function() {
                            return m('div[style="padding-left:5px"]',
                                    [m('p',
                                        [m('b', item.data.node.title + ':')]
                                )]
                            );
                        }
                    });
                }
            }
            else if (item.data.kind === 'folder' || item.data.kind === 'node') {
                columns.push({
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : false,
                    custom : function() {
                        if (item.data.node.url !== '') {
                            return m('a', { href : item.data.node.url, target : '_blank' }, item.data.node.title);
                        } else {
                            return m('span', item.data.node.title);
                        }

                    }
                });
            }

            else {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function() {
                        return "Editing Settings";

                    }
                },
                {
                    data : 'permission',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        return  m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    change_permissions(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'private', selected : item.data.event.permission === 'private' ? 'selected': ''}, 'Private'),
                                    m('option', {value: 'public', selected : item.data.event.permission === 'public' ? 'selected': ''}, 'Public')
                            ])
                        ]);
                    }
                });
            }

            return columns;
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover',
        resolveRefreshIcon : function() {
          return m('i.fa.fa-refresh.fa-spin');
        }
    };
    var grid = new Treebeard(tbOptions);
    expandOnLoad.call(grid.tbController);
}

module.exports = ProjectWiki;
