'use strict';

var m = require('mithril');

var Fangorn = require('js/fangorn').Fangorn;


// Define Fangorn Button Actions
var _figshareItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
        if (tb.options.placement !== 'fileview') {
            // If File and FileRead are not defined dropzone is not supported and neither is uploads
            if (window.File && window.FileReader && item.data.permissions && item.data.permissions.edit && item.kind === 'folder') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._uploadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-upload',
                        className: 'text-success'
                    }, 'Upload')
                );
                if (item.data.rootFolderType === 'project') {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function () {
                                tb.toolbarMode(Fangorn.Components.toolbarModes.ADDFOLDER);
                            },
                            icon: 'fa fa-plus',
                            className: 'text-success'
                        }, 'Create Folder'));
                }
            }

            // Download file or Download-as-zip
            if (item.kind === 'file') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._downloadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
            }
            else {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) { Fangorn.ButtonEvents._downloadZipEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download as zip')
                );
            }

            // All files are viewable on the OSF.
            if (item.kind === 'file' && item.data.permissions && item.data.permissions.view) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._gotoFileEvent.call(tb, item);
                        },
                        icon: 'fa fa-file-o',
                        className: 'text-info'
                    }, 'View'));
            }

            // Files and folders can be deleted if private.
            var isPrivate = (item.data.extra && item.data.extra.status !== 'public');
            if (isPrivate && item.data.permissions && item.data.permissions.edit) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._removeEvent.call(tb, event, tb.multiselected());
                        },
                        icon: 'fa fa-trash',
                        className: 'text-danger'
                    }, 'Delete')
                );
            }

            // Files are only viewable on figshare if they are public
            if (item.kind === 'file' && item.data.permissions && item.data.permissions.view && item.data.extra.status === 'public') {
                buttons.push(
                    m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                        m('i.fa.fa-external-link'),
                        m('span', 'View on figshare')
                    ])
                );
            }
        }
        return m('span', buttons); // Tell fangorn this function is used.
    }
};


Fangorn.config.figshare = {
    // Fangorn options are called if functions, so return a thunk that returns the column builder
    itemButtons: _figshareItemButtons
};
