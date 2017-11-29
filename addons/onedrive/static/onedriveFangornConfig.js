'use strict';
/**
 * OneDrive FileBrowser configuration module.
 */

var m = require('mithril');
var Fangorn = require('js/fangorn').Fangorn;

// Define Fangorn Button Actions
var _onedriveItemButtons = {
    view: function (ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var buttons = [];
        if (tb.options.placement !== 'fileview') {
            if (item.kind === 'folder') {
                // Download Zip File
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._downloadZipEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download as zip')
                );
            }
            else if (item.kind === 'file') {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            Fangorn.ButtonEvents._downloadEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                if (item.data.permissions && item.data.permissions.view) {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function(event) {
                                Fangorn.ButtonEvents._gotoFileEvent.call(tb, item);
                            },
                            icon: 'fa fa-file-o',
                            className : 'text-info'
                        }, 'View')
                    );
                    if (!item.data.permissions.private) {
                        buttons.push(
                            m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                                m('i.fa.fa-external-link'),
                                m('span', 'View on OneDrive')
                            ])
                        );
                    }
                }
            }
        }

        return m('span', buttons); // Tell fangorn this function is used.
    }
};


// Register configuration
Fangorn.config.onedrive = {
    itemButtons: _onedriveItemButtons,
};
