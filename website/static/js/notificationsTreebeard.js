'use strict';

var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
var $tb = require('js/treebeardHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');


function subscribe(item, notificationType) {
    var id = item.parent().data.node.id;
    var event = item.data.event.title;
    var payload = {
        'id': id,
        'event': event,
        'notification_type': notificationType
    };
    $osf.postJSON(
        '/api/v1/subscriptions/',
        payload
    ).done(function(){
        //'notfiy-success' is to override default class 'success' in treebeard
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.event.notificationType = notificationType;
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

var tooltipConfig = function(element, isInit) {
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
            $tb.expandOnLoad.call(tb);
        },
        resolveRows: function notificationResolveRows(item){
            var options = [];
            console.log(item)
            if (item.data.event !== undefined) {
                options = [
                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                    m('option', {value: 'email_transactional', selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                ];
            }
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
                                                m('span[class="text-muted"]', ' No configured projects.')]
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
                            return m('div[style="padding-left:5px; padding-bottom:50px"]', [
                                m('p', [
                                    m('b', item.data.node.title + ':  '),
                                        m('span[class="fa fa-info-circle"]', {
                                            'data-toggle': 'tooltip',
                                            'title':item.data.node.help,
                                            'config': tooltipConfig,
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
                if (item.data.event.title !== 'mailing_list_events') {
                    options.push(m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily'));
                }
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
                        var mentionsInTitle = ~item.data.event.title.indexOf('mentions');
                        var notificationOptions;
                        if (mentionsInTitle)
                            notificationOptions = [m('option', {value: 'email_transactional', selected: 'email_transactional', disabled: true}, 'Instantly')];
                        else {
                            var type = item.data.event.notificationType;
                            notificationOptions = [
                                m('option', {value: 'none', selected : type === 'none' ? 'selected': ''}, 'Never'),
                                m('option', {value: 'email_transactional', selected : type === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                m('option', {value: 'email_digest', selected : type === 'email_digest' ? 'selected': ''}, 'Daily')
                            ];
                        }
                        return m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                notificationOptions
                            )]
                        );
                    }
                });
            }
            else {
                if (item.data.event.title !== 'mailing_list_events') {
                    options.push(m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily'));
                    options.push(m('option', {value: 'adopt_parent', selected: item.data.event.notificationType === 'adopt_parent' ? 'selected' : ''},
                                                 'Adopt setting from parent project ' + displayParentNotificationType(item)));
                }
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
                                options)
                        ]);
                    }
                });
            }

            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
    $tb.expandOnLoad.call(grid);
}

module.exports = ProjectNotifications;
