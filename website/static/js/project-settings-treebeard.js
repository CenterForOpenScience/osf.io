var $ = require('jquery');
require('../vendor/bower_components/slickgrid/lib/jquery.event.drag-2.2.js');
var m = require('mithril');
var Treebeard = require('treebeard');

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
    // this = treebeard object;
    // Item = item acted on
    if (item.children.length > 0) {
        if (item.open) {
            return m("i.icon.icon-folder-open", " ");
        }
        return m("i.icon.icon-folder-close", " ");
    } else if (item.data.kind === 'node') {
            return m("i.icon.icon-folder-close", " ");
    }
    return m("i.icon.icon-circle-blank");
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
        columnTitles : function _conferenceColumnTitles(item, col) {
             return [
                {
                    title: "Project",
                    width: "60%",
                    sortType : "text",
                    sort : true
                },
                {
                    title: "Notification Type",
                    width : "40%",
                    sort : true

                }
            ]},
        resolveRows : function _conferenceResolveRows(item){
            var default_columns = [];

            if (item.data.kind === 'folder' || item.data.kind === 'node') {
                default_columns.push({
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : true,
                    custom : function() {
                        return m('a', { href : item.data.nodeUrl, target : '_blank' }, item.data.title );
                    }
                });
            }
            else if (item.parent().data.kind === 'folder' && item.data.kind === 'event') {
                default_columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : true,
                    custom : function(item, col) {
                        return item.data.description;

                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function(item, col) {
                        return m("div[style='padding-right:10px']",
                            [m("select.form-control", {
                                id: item.parent().data.node_id,
                                name: item.data.title,
                                onchange: function(ev) {
                                    item.data.notificationType = ev.target.value;
                                }},
                                [
                                    m("option", {value: "none", selected : item.data.notificationType === "none" ? "selected": ""}, "None"),
                                    m("option", {value: "email_transactional", selected : item.data.notificationType === "email_transactional" ? "selected": ""}, "Emails"),
                                    m("option", {value: "email_digest", selected : item.data.notificationType === "email_digest" ? "selected": ""}, "Email Digest")
                            ])
                        ]);
                    }
                });
            }
            else {
                default_columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : true,
                    custom : function() {
                        return item.data.description;

                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        return  m("div[style='padding-right:10px']",
                            [m("select.form-control", {
                                id: item.parent().data.node_id,
                                name: item.data.title,
                                onchange: function(ev) {
                                    item.data.notificationType = ev.target.value;
                                }},
                                [
                                    m("option", {value: "adopt_parent", selected: item.data.notificationType === "adopt_parent" ? "selected" : ""}, "Adopt setting from parent project"),
                                    m("option", {value: "none", selected : item.data.notificationType === "none" ? "selected": ""}, "None"),
                                    m("option", {value: "email_transactional",  selected : item.data.notificationType === "email_transactional" ? "selected": ""}, "Emails"),
                                    m("option", {value: "email_digest", selected : item.data.notificationType === "email_digest" ? "selected": ""}, "Email Digest")
                            ])
                        ])
                    }
                });
            }

            return default_columns;
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
