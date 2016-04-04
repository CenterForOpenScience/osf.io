
var m = require('mithril');
var Components = {};

Components.modal = {
    view: function(ctrl, args){
        var id = args.id; // This is required
        var header = args.header || '';
        var body = args.body || '';
        var footer = args.footer || '';
        return m('#' + id + '.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
            m('.modal-dialog',
                m('.modal-content', [
                    header,
                    body,
                    footer
                ])
            )
        );
    }
};

module.exports = Components;