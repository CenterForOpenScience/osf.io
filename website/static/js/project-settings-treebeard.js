'use strict';

var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');
require('../vendor/bower_components/slickgrid/lib/jquery.event.drag-2.2.js');
var m = require('mithril');
var Treebeard = require('treebeard');
require('../css/fangorn.css');


function resolveToggle(item) {
    var toggleMinus = m('i.icon-minus', ' '),
        togglePlus = m('i.icon-plus', ' ');

    if (item.children.length > 0) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    item.open = true;
    return '';
}

function resolveIcon(item) {
    if (item.children.length > 0) {
        if (item.open) {
            return m('i.icon.icon-folder-open', ' ');
        }
        return m('i.icon.icon-folder-close', ' ');
    }
}

function expandOnLoad() {
    var tb = this;
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

function subscribe(id, event, notification_type) {
    var payload = {
        'id': id,
        'event': event,
        'notification_type': notification_type
    };
    $osf.postJSON(
        '/api/v1/subscriptions/',
        payload
    ).fail(function() {
        bootbox.alert('Could not update notification preferences.');
    });
}


function displayParentNotificationType(item){
    var notificationTypeDescriptions = {
        'email_transactional': 'Emails',
        'email_digest': 'Email Digest',
        'adopt_parent': 'Adopt setting from parent project',
        'none': 'None'
    };

    if (item.data.parent_notification_type) {
        if (item.parent().parent().parent() === undefined) {
            return '(' + notificationTypeDescriptions[item.data.parent_notification_type] + ')';
        }
    }
    return '';
}


function ProjectNotifications(data) {

    //  Treebeard version
    var tbOptions = {
        divID: 'grid',
        filesData: data,
        rowHeight : 40,         // user can override or get from .tb-row height
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        resolveIcon : resolveIcon,
        hideColumnTitles: true,
        onload: function () {
            var tb = this;
            expandOnLoad.call(tb);
        },
        columnTitles : function notificationColumnTitles(item, col) {
            return [
                {
                    title: 'Project',
                    width: '60%',
                    sortType : 'text',
                    sort : false
                },
                {
                    title: 'Notification Type',
                    width : '40%',
                    sort : false

                }
            ]},
        resolveRows : function notificationResolveRows(item){
            var columns = [];
            var iconcss = 'test';
            // check if should not get icon
            if(item.children.length < 1 ){
                iconcss = 'tb-no-icon';
            }
            if (item.data.kind === 'heading') {
                 columns.push({
                    data : 'project',  // Data field name
                    folderIcons : false,
                    filter : true,
                    sortInclude : false,
                    custom : function() {
                        return m("div[style='padding-left:5px']",
                                [m('b', [m('p', item.data.node.title + ':')])
                                ])
                    }
                });
            }
            else if (item.data.kind === 'folder' || item.data.kind === 'node') {
                columns.push({
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : false,
                    custom : function() {
                        return m('a', { href : item.data.node.url, target : '_blank' }, item.data.node.title );
                    }
                });
            }
            else if (item.parent().data.kind === 'folder' || item.parent().data.kind === 'heading' && item.data.kind === 'event') {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function(item, col) {
                        return item.data.event.description;

                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function(item, col) {
                        return m("div[style='padding-right:10px']",
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    item.data.notificationType = ev.target.value;
                                    subscribe(item.parent().data.node.id, item.data.event.title, item.data.event.notificationType)
                                }},
                                [
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'None'),
                                    m('option', {value: 'email_transactional', selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Emails'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Email Digest')
                            ])
                        ]);
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
                        return item.data.event.description;

                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        return  m("div[style='padding-right:10px']",
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    item.data.event.notificationType = ev.target.value;
                                    subscribe(item.parent().data.node.id, item.data.event.title, item.data.event.notificationType)
                                }},
                                [
                                    m('option', {value: 'adopt_parent',
                                                 selected: item.data.event.notificationType === 'adopt_parent' ? 'selected' : ''},
                                                 'Adopt setting from parent project ' + displayParentNotificationType(item)),
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'None'),
                                    m('option', {value: 'email_transactional',  selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Emails'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Email Digest')
                            ])
                        ])
                    }
                });
            }

            return columns;
        },
        sortButtonSelector : {
            up : 'i.icon-chevron-up',
            down : 'i.icon-chevron-down'
        },
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : 'fangorn-hover'
    };
    var grid = new Treebeard(tbOptions);
}

module.exports = ProjectNotifications;
