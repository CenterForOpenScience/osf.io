'use strict';
/**
 * IQB-RIMS FileBrowser configuration module.
 */

var m = require('mithril');
var Fangorn = require('js/fangorn').Fangorn;
var storageAddons = require('json-loader!storageAddons.json');

// Define Fangorn Button Actions
var _iqbrimsItemButtons = {
    view : function(ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var rowButtons = [];
        if (tb.options.placement !== 'fileview') {
            if (item.kind === 'file') {
                rowButtons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) { Fangorn.ButtonEvents._downloadEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                if (item.data.permissions && item.data.permissions.view) {
                    rowButtons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                Fangorn.ButtonEvents.gotoFileEvent.call(tb, item, '/');
                            },
                            icon: 'fa fa-file-o',
                            className: 'text-info'
                        }, 'View'));
                }
                if(storageAddons[item.data.provider].externalView) {
                    var providerFullName = storageAddons[item.data.provider].fullName;
                    rowButtons.push(
                        m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                            m('i.fa.fa-external-link'),
                            m('span', 'View on ' + providerFullName)
                        ])
                    );
                }
            } else if (item.data.provider) {
                rowButtons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) { Fangorn.ButtonEvents._downloadZipEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download as zip')
                );
            }
            return m('span', rowButtons);
        }
    }
};


// Register configuration
Fangorn.config.iqbrims = {
    itemButtons: _iqbrimsItemButtons,
};
