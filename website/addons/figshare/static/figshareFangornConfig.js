'use strict';

var m = require('mithril');

var Fangorn = require('js/fangorn');


// Define Fangorn Button Actions
function _figshareDefineToolbar (item) {
    var tb = this;  // jshint ignore:line
    var buttons = [];

    // If File and FileRead are not defined dropzone is not supported and neither is uploads
    if (window.File && window.FileReader && item.data.permissions && item.data.permissions.edit && item.kind === 'folder') {
        buttons.push(
            m.component(Fangorn.Components.button, {
                onclick: function (event) {
                    Fangorn.ButtonEvents._uploadEvent.call(tb, event, item);
                },
                tooltip: 'Upload files to figshare.',
                icon: 'fa fa-upload',
                className : 'text-success'
            }, 'Upload')
        );
    }
    if (item.kind === 'file' && item.data.extra && item.data.extra.status === 'public') {
        buttons.push(
            m.component(Fangorn.Components.button, {
                onclick: function (event) {
                    Fangorn.ButtonEvents._downloadEvent.call(tb, event, item);
                },
                tooltip: 'Download file to your computer.',
                icon: 'fa fa-download',
                className : 'text-info'
            }, 'Download')
        )   
    }

    // Files can be deleted if private or if parent contains more than one child
    var privateOrSiblings = (item.data.extra && item.data.extra.status !== 'public') ||
        item.parent().children.length > 1;
    if (item.kind === 'file' && privateOrSiblings) {
        buttons.push(
            m.component(Fangorn.Components.button, {
                onclick: function (event) {
                    Fangorn.ButtonEvents._removeEvent.call(tb, event, tb.multiselected());
                },
                tooltip: 'Delete file.',
                icon: 'fa fa-trash',
                className : 'text-danger'
            }, 'Delete')
        );
    }

    return buttons; // Tell fangorn this function is used.
}


Fangorn.config.figshare = {
    // Fangorn options are called if functions, so return a thunk that returns the column builder
    defineToolbar: _figshareDefineToolbar
};
