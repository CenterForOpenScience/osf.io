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

function subscribe(item, notification_type) {
    var id = item.parent().data.node.id;
    var event = item.data.event.title;
    var payload = {
        'id': id,
        'event': event,
        'notification_type': notification_type
    };
    $osf.postJSON(
        '/api/v1/subscriptions/',
        payload
    ).done(function(){
        //'notfiy-success' is to override default class 'success' in treebeard
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.event.notificationType = notification_type;
    }).fail(function() {
        item.notify.update('Could not update settings', 'notify-danger', 1, 2000);
    });
}

function displayParentNotificationType(item){
    var notificationTypeDescriptions = {
        'email_transactional': 'Instantly',
        'email_digest': 'Daily',
        'adopt_parent': 'Adopt setting from parent project',
        'none': 'Never'
    };

    if (item.data.event.parent_notification_type) {
        if (item.parent().parent().parent() === undefined) {
            return '(' + notificationTypeDescriptions[item.data.event.parent_notification_type] + ')';
        }
    }
    return '';
}

var popOver = function(element, isInit) {
    if (!isInit) {
        $(element).tooltip();
    }
};

function ProjectNotifications(data) {

    //  Treebeard version
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: 'grid',
        filesData: data,
        naturalScrollLimit : 0,
        onload : function () {
            var tb = this;
            expandOnLoad.call(tb);
        },
        resolveRows: function notificationResolveRows(item){
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
                            var globalNotificationsMessage = 'These are default settings for new ' +
                                'projects you create or are added to. Modifying these settings will ' +
                                'not modify settings on existing projects.';
                            var projectNotificationsMessage = 'These are settings for each of your ' +
                                'projects. Modifying these settings will only modify the settings ' +
                                'for the selected project.';
                            return m('div[style="padding-left:5px; padding-bottom:50px"]', [
                                m('p', [
                                    m('b', item.data.node.title + ':  '),
                                    item.data.node.title === 'Default Global Notification Settings' ?
                                        m('span[class="fa fa-info-circle"]', {
                                            'data-toggle': 'tooltip',
                                            'title':globalNotificationsMessage,
                                            'config': popOver,
                                            'data-placement': 'bottom'
                                        }) :
                                        m('span[class="fa fa-info-circle"]', {
                                            'data-toggle': 'tooltip',
                                            'title':projectNotificationsMessage,
                                            'config': popOver,
                                            'data-placement': 'bottom'
                                        })
                                ])
                            ]);
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
            else if (item.parent().data.kind === 'folder' || item.parent().data.kind === 'heading' && item.data.kind === 'event') {
                var mentionsInTitle = ~item.data.event.title.indexOf('mentions');
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
                        return m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                [
                                    mentionsInTitle ?
                                        null :
                                        m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                                    mentionsInTitle ?
                                        null :
                                        m('option', {value: 'email_transactional', selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                    mentionsInTitle ?
                                        null :
                                        m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily'),
                                    mentionsInTitle ?
                                        m('option', {value: 'email_transactional', selected: 'email_transactional', disabled: true}, 'Instantly') :
                                        null,
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
                        return  m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'adopt_parent',
                                                 selected: item.data.event.notificationType === 'adopt_parent' ? 'selected' : ''},
                                                 'Adopt setting from parent project ' + displayParentNotificationType(item)),
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                                    m('option', {value: 'email_transactional',  selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily')
                            ])
                        ]);
                    }
                });
            }

            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
}

module.exports = ProjectNotifications;
