'use strict';

var m = require('mithril');

var Fangorn = require('js/fangorn');
var FGButton = Fangorn.Components.button

var waterbutler = require('js/waterbutler');

var _shareLatexItemButtons = {
    view : function(ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var rowButtons = [];
        var mode = args.mode;
        /**
         * Download button in Action Column
         * @param event DOM event object for click
         * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
         * @param {Object} col Information pertinent to that column where this upload event is run from
         * @private
         */
        function _downloadEvent (event, item, col) {
            try {
                event.stopPropagation();
            } catch (e) {
                window.event.cancelBubble = true;
            }
            window.location = waterbutler.buildTreeBeardDownload(item);
        }

        function _downloadZipEvent (event, item, col) {
            try {
                event.stopPropagation();
            } catch (e) {
                window.event.cancelBubble = true;
            }
            window.location = waterbutler.buildTreeBeardDownloadZip(item);
        }
        if (tb.options.placement !== 'fileview') {
            if (item.kind === 'file') {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function (event) { _downloadEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download')
                );
                if (item.data.permissions && item.data.permissions.view) {
                    rowButtons.push(
                        m.component(FGButton, {
                            onclick: function (event) {
                                gotoFileEvent.call(tb, item);
                            },
                            icon: 'fa fa-file-o',
                            className: 'text-info'
                        }, 'View'));
                }
            } else if (item.data.provider) {
                rowButtons.push(
                    m.component(FGButton, {
                        onclick: function (event) { _downloadZipEvent.call(tb, event, item); },
                        icon: 'fa fa-download',
                        className: 'text-primary'
                    }, 'Download as zip')
                );
            }
            return m('span', rowButtons);
        }
    }
};

Fangorn.config.sharelatex = {
    itemButtons: _shareLatexItemButtons
};
