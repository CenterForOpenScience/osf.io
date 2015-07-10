'use strict';

var m = require('mithril');

var Fangorn = require('js/fangorn');


// Define Fangorn Button Actions
var _figshareItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
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
        }
        if (item.kind === 'file' && item.data.extra && item.data.extra.status === 'public') {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        Fangorn.ButtonEvents._downloadEvent.call(tb, event, item);
                    },
                    icon: 'fa fa-download',
                    className: 'text-info'
                }, 'Download')
            );
        }
        // Files can be deleted if private or if it is in a dataset that contains more than one file
        var privateOrSiblings = (item.data.extra && item.data.extra.status !== 'public') ||
            (!item.parent().data.isAddonRoot && item.parent().children.length > 1);
        if (item.kind === 'file' && privateOrSiblings && item.data.permissions && item.data.permissions.edit) {
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
        if (item.kind === 'file' && item.data.permissions && item.data.permissions.view) {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function(event) {
                        Fangorn.ButtonEvents._gotoFileEvent.call(tb, item);
                    },
                    icon: 'fa fa-file-o',
                    className : 'text-info'
                }, 'View'));
        }
        return m('span', buttons); // Tell fangorn this function is used.
    }
};


Fangorn.config.figshare = {
    // Fangorn options are called if functions, so return a thunk that returns the column builder
    itemButtons: _figshareItemButtons
};
