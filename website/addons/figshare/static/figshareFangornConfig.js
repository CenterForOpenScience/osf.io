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
            { name : 'uploadFiles', template : function(){
                return m('.fangorn-toolbar-icon.text-success', {
                        onclick : function(event) { Fangorn.ButtonEvents._uploadEvent.call(tb, event, item); } 
                    },[
                    m('i.fa.fa-upload'),
                    m('span.hidden-xs','Upload')
                ]);
            }}
        );
    }
    if (item.kind === 'file' && item.data.extra && item.data.extra.status === 'public') {
        buttons.push(
            { name : 'downloadFile', template : function(){
                return m('.fangorn-toolbar-icon.text-info', {
                        onclick : function(event) { Fangorn.ButtonEvents._downloadEvent.call(tb, event, item); } 
                    },[
                    m('i.fa.fa-download'),
                    m('span.hidden-xs','Download')
                ]);
            }}
        )   
    }

    // Files can be deleted if private or if parent contains more than one child
    var privateOrSiblings = (item.data.extra && item.data.extra.status !== 'public') ||
        item.parent().children.length > 1;
    if (item.kind === 'file' && privateOrSiblings) {
        buttons.push(
            { name : 'deleteFile', template : function(){
                return m('.fangorn-toolbar-icon.text-danger', {
                        onclick : function(event) { Fangorn.ButtonEvents._removeEvent.call(tb, event, tb.multiselected); } 
                    },[
                    m('i.fa.fa-times'),
                    m('span.hidden-xs','Delete')
                ]);
            }}
        );
    }

    item.icons = buttons;

    return true; // Tell fangorn this function is used. 
}


Fangorn.config.figshare = {
    // Fangorn options are called if functions, so return a thunk that returns the column builder
    defineToolbar: _figshareDefineToolbar,
};
