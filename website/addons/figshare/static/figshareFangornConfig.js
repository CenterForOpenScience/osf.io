'use strict';

var m = require('mithril');

var Fangorn = require('js/fangorn');


// Define Fangorn Button Actions
function _fangornActionColumn (item, col) {
    var self = this;  // jshint ignore:line
    var buttons = [];

    // If File and FileRead are not defined dropzone is not supported and neither is uploads
    if (window.File && window.FileReader && item.data.permissions.edit && item.kind === 'folder') {
        buttons.push({
            'name' : '',
            'tooltip' : 'Upload files',
            'icon' : 'fa fa-upload',
            'css' : 'fangorn-clickable btn btn-default btn-xs',
            'onclick' : Fangorn.ButtonEvents._uploadEvent
        });
    }
    if (item.kind === 'file' && item.data.extra && item.data.extra.status === 'public') {
        buttons.push({
            'name' : '',
            'tooltip' : 'Download file',
            'icon' : 'fa fa-download',
            'css' : 'btn btn-info btn-xs',
            'onclick' : Fangorn.ButtonEvents._downloadEvent
        });
    }

    // Files can be deleted if private or if parent contains more than one child
    var privateOrSiblings = (item.data.extra && item.data.extra.status !== 'public') ||
        item.parent().children.length > 1;
    if (item.kind === 'file' && privateOrSiblings) {
        buttons.push({
            'name' : '',
            'icon' : 'fa fa-times',
            'tooltip' : 'Delete',
            'css' : 'm-l-lg text-danger fg-hover-hide',
            'style' : 'display:none',
            'onclick' : Fangorn.ButtonEvents._removeEvent
        });
    }

    return buttons.map(function(btn) {
        return m('span', { 'data-col' : item.id }, [ m('i',{
            'class' : btn.css,
            style : btn.style,
            'data-toggle' : 'tooltip', title : btn.tooltip, 'data-placement': 'bottom',
            onclick: function(event){ btn.onclick.call(self, event, item, col); }
        },
            [ m('span', { 'class' : btn.icon}, btn.name) ])
        ]);
    });
}

Fangorn.config.figshare = {
    // Fangorn options are called if functions, so return a thunk that returns the column builder
    resolveActionColumn: function() {return _fangornActionColumn;}
};
