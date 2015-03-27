'use strict';

var m = require('mithril');
var $ = require('jquery');
var Fangorn = require('js/fangorn');

function refreshDataverseTree(grid, item, state) {
    var data = item.data || {};
    var url = item.data.urls.state + '?' + $.param({state: state});
    data.state = state;
    $.ajax({
        type: 'get',
        url: url,
        success: function(data) {
            // Update the item with the new state data
            $.extend(item.data, data[0]);
            grid.updateFolder(null, item);
        }
    });
}

function _uploadUrl(item, file) {
    return item.data.urls.upload + '?' + $.param({name: file.name});
}

function _downloadEvent(event, item, col) {
    event.stopPropagation();
    window.location = item.data.urls.download;
}

// Define Fangorn Button Actions
function _dataverseDefineToolbar (item) {
    var self = this;
    var buttons = [];

    function _uploadEvent (event, item, col){
        event.stopPropagation();
        this.dropzone.hiddenFileInput.click();
        this.dropzoneItemCache = item;
    }

    function dataverseRelease(event, item, col) {
        var self = this; // treebeard
        var url = item.data.urls.release;
        var modalContent = [
            m('h3', 'Release this study?'),
            m('p.m-md', 'By releasing this study, all content will be made available through the Harvard Dataverse using their internal privacy settings, regardless of your OSF project settings.'),
            m('p.font-thick.m-md', 'Are you sure you want to release this study?')
        ];
        var modalActions = [
            m('button.btn.btn-default.m-sm', { 'onclick' : function (){ self.modal.dismiss(); }},'Cancel'),
            m('button.btn.btn-primary.m-sm', { 'onclick' : function() { releaseStudy(); } }, 'Release Study')
        ];

        this.modal.update(modalContent, modalActions);

        function releaseStudy() {
            self.modal.dismiss();
            item.notify.update('Releasing Study', 'info', 1, 3000);
            $.osf.putJSON(
                url,
                {}
            ).done(function(data) {
                var modalContent = [
                    m('p.m-md', 'Your study has been released. Please allow up to 24 hours for the released version to appear on your OSF project\'s file page.')
                ];
                var modalActions = [
                    m('button.btn.btn-primary.m-sm', { 'onclick' : function() { self.modal.dismiss(); } }, 'Okay')
                ];
                self.modal.update(modalContent, modalActions);
            }).fail( function(args) {
                var message = args.responseJSON.code === 400 ?
                    'Error: Something went wrong when attempting to release your study.' :
                    'Error: This version has already been released.';

                var modalContent = [
                    m('p.m-md', message)
                ];
                var modalActions = [
                    m('button.btn.btn-primary.m-sm', { 'onclick' : function() { self.modal.dismiss(); } }, 'Okay')
                ];
                self.modal.update(modalContent, modalActions);
                //self.updateItem(row);
            });
        }
    }

    if (item.kind === 'folder' && item.data.addonFullname && item.data.state === 'draft' && item.data.permissions.edit) {
        buttons.push(
            { name : 'uploadFiles', template : function(){
                return m('.fangorn-toolbar-icon.text-success', {
                        onclick : function(event) { _uploadEvent.call(self, event, item); } 
                    },[
                    m('i.fa.fa-upload'),
                    m('span.hidden-xs','Upload')
                ]);
            }},
            { name : 'dataverseRelease', template : function(){
                return m('.fangorn-toolbar-icon.text-primary', {
                        onclick : function(event) { _uploadEvent.call(self, event, item); } 
                    },[
                    m('i.fa.fa-globe'),
                    m('span.hidden-xs','Release Study')
                ]);
            }}            
        );
    } else if (item.kind === 'folder' && !item.data.addonFullname) {
        buttons.push(
            { name : 'uploadFiles', template : function(){
                return m('.fangorn-toolbar-icon.text-success', {
                        onclick : function(event) { _uploadEvent.call(self, event, item); } 
                    },[
                    m('i.fa.fa-upload'),
                    m('span.hidden-xs','Upload')
                ]);
            }}
        );
    } else if (item.kind === 'file') {
        buttons.push(
            { name : 'downloadFile', template : function(){
                return m('.fangorn-toolbar-icon.text-info', {
                        onclick : function(event) { _downloadEvent.call(self, event, item); } 
                    },[
                    m('i.fa.fa-download'),
                    m('span.hidden-xs','Download')
                ]);
            }}
        );
        if (item.parent().data.state === 'draft' && item.data.permissions.edit) {
            buttons.push(
                { name : 'deleteFile', template : function(){
                    return m('.fangorn-toolbar-icon.text-danger', {
                            onclick : function(event) { Fangorn.ButtonEvents._removeEvent.call(self, event, item); } 
                        },[
                        m('i.fa.fa-times'),
                        m('span.hidden-xs','Delete')
                    ]);
                }}
                );
        }
    }
    item.icons = buttons;

    return true; // Tell fangorn this function is used. 
    
}

function _fangornDataverseTitle(item, col) {
    var tb = this;
    if (item.data.addonFullname) {
        var contents = [m('dataverse-name', item.data.name + ' ')];
        if (item.data.hasReleasedFiles) {
            if (item.data.permissions.edit) {
                var options = [
                    m('option', {selected: item.data.state === 'draft', value: 'draft'}, 'Draft'),
                    m('option', {selected: item.data.state === 'released', value: 'released'}, 'Released')
                ];
                contents.push(
                    m('span', [
                        m('select', {
                            class: 'dataverse-state-select',
                            onchange: function(e) {
                                refreshDataverseTree(tb, item, e.target.value);
                            },
                        }, options)
                    ])
                );
            } else {
                contents.push(
                    m('span', '[Released]')
                );
            }
        }
        return m('span', contents);
    } else {
        return m('span',[
            m('dataverse-name', {
                onclick: function() {
                    window.location = item.data.urls.view;
                },
                'data-toggle': 'tooltip',
                title: 'View file',
                'data-placement': 'bottom'
            }, item.data.name
             )
        ]);
    }
}

function _fangornColumns(item) {
    var columns = [];
    columns.push(
    {
        data : null,
        folderIcons: false,
        filter : false,
        custom : function(){
            return m('div.fangorn-select-toggle', m('i.fa.fa-square-o'));
        }
    },
    {
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: _fangornDataverseTitle
    });

    if (this.options.placement === 'project-files') {
        columns.push(
            {
                data: 'downloads',
                filter: false,
                css: ''
            }
        );
    }
    return columns;
}

function _fangornFolderIcons(item){
    if(item.data.iconUrl){
        return m('img',{src:item.data.iconUrl, style:{width:'16px', height:'auto'}}, ' ');
    }
    return undefined;
}

function _fangornDeleteUrl(item) {
    return item.data.urls.delete;
}

function _fangornLazyLoad(item) {
    return item.data.urls.fetch;
}

function _canDrop(item) {
    return item.data.provider &&
        item.kind === 'folder' &&
        item.data.permissions.edit &&
        item.data.state === 'draft'
}

Fangorn.config.dataverse = {
    // Handle changing the branch select
    folderIcon: _fangornFolderIcons,
    resolveDeleteUrl: _fangornDeleteUrl,
    resolveRows: _fangornColumns,
    lazyload:_fangornLazyLoad,
    uploadUrl: _uploadUrl,
    canDrop: _canDrop,
    defineToolbar: _dataverseDefineToolbar,

};
