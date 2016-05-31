'use strict';

var $ = require('jquery');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('js/osfHelpers');
var $tb = require('js/treebeardHelpers');
var projectSettingsTreebeardBase = require('js/projectSettingsTreebeardBase');

function subscribe(item, notification_type, reload) {
    var id = item.data.node.id;
    var url = '/api/v1/project/' + id + '/mailing_list/';  // TODO [OSF-6400]: Update to V2
    var method = notification_type === 'enabled' ? 'POST' : 'DELETE';
    $.ajax({
        url: url,
        type: method,
        dataType: 'json'
    }).done(function(){
        //'notify-success' is to override default class 'success' in treebeard
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.node.mailing_list = notification_type;
        reload();
    }).fail(function() {
        item.notify.update('Could not update settings', 'notify-danger', 1, 2000);
    });
}

function ProjectMailingList(data, reload) {

    //  Treebeard version
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: 'mailingListGrid',
        filesData: data,
        naturalScrollLimit : 0,
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
                },
                {
                    data : 'mailingListEnabled',
                    folderIcons : false,
                    filter : false,
                    custom : function(item, col) {
                        return m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value, reload);
                                }},
                                [
                                    m('option', {value: 'disabled', selected : item.data.node.mailing_list === 'disabled' ? 'selected': ''}, 'Mailing List Disabled'),
                                    m('option', {value: 'enabled', selected : item.data.node.mailing_list === 'enabled' ? 'selected': ''}, 'Mailing List Enabled'),
                            ])
                        ]);
                    }
                }
                );
            }
            return columns;
        }
    });
    var mailingListGrid = new Treebeard(tbOptions);
    $tb.expandOnLoad.call(mailingListGrid.tbController);
}

module.exports = ProjectMailingList;
