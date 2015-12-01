'use strict';

var m = require('mithril');
var Fangorn = require('js/fangorn');

// Define Fangorn Button Actions
var _dryadItemButtons = {
    view: function (ctrl, args, children) {
        var buttons = [];
        var tb = args.treebeard;
        var item = args.item;
        if (tb.options.placement !== 'fileview') {
            // If File and FileRead are not defined dropzone is not supported and neither is uploads
            if (item.kind === 'file' && item.data.extra && item.data.extra.status === 'public') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._downloadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._gotoFileEvent.call(tb, item);
                        },
                        icon: 'fa fa-file-o',
                        className: 'text-info'
                    }, 'View'));
            }
            // Files can be deleted if private or if it is in a dataset that contains more than one file
            var privateOrSiblings = (item.data.extra && item.data.extra.status !== 'public') ||
                (!item.parent().data.isAddonRoot && item.parent().children.length > 1);
            if (item.kind === 'file' && item.data.permissions && item.data.permissions.view) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._gotoFileEvent.call(tb, item);
                        },
                        icon: 'fa fa-file-o',
                        className: 'text-info'
                    }, 'View'));
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            var fileurl = item.data.extra.webView;

                            window.open(fileurl, '_blank');
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
            }
            if (item.kind === 'file' && item.data.permissions && item.data.permissions.view && item.data.extra.status === 'public') {
                buttons.push(
                    m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                        m('i.fa.fa-external-link'),
                        m('span', 'View on dryad')
                    ])
                );
            }
        }
        return m('span', buttons); // Tell fangorn this function is used.
    }
};

Fangorn.config.dryad = {
    // Fangorn options are called if functions, so return a thunk that returns the column builder
    itemButtons: _dryadItemButtons
};
