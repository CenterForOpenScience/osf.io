'use strict';

var m = require('mithril');
var $ = require('jquery');
var Fangorn = require('fangorn');

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
function _fangornActionColumn (item, col) {
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
            {
                'name' : '',
                'tooltip' : 'Upload file',
                'icon' : 'fa fa-upload',
                'css' : 'fangorn-clickable btn btn-default btn-xs',
                'onclick' : _uploadEvent
            },
            {
                'name' : ' Release Study',
                'tooltip' : '',
                'icon' : 'fa fa-globe',
                'css' : 'btn btn-primary btn-xs',
                'onclick' : dataverseRelease
            }
        );
    } else if (item.kind === 'folder' && !item.data.addonFullname) {
        buttons.push(
            {
                'name' : '',
                'tooltip' : 'Upload file',
                'icon' : 'fa fa-upload',
                'css' : 'fangorn-clickable btn btn-default btn-xs',
                'onclick' : _uploadEvent
            }
        );
    } else if (item.kind === 'file') {
        buttons.push({
            name : '',
            'tooltip' : 'Download file',
            icon : 'fa fa-download',
            css : 'btn btn-info btn-xs',
            onclick: _downloadEvent
        });
        if (item.parent().data.state === 'draft' && item.data.permissions.edit) {
            buttons.push({
                name: '',
                tooltip : 'Delete',
                icon: 'fa fa-times',
                css: 'm-l-lg text-danger fg-hover-hide',
                style: 'display:none',
                onclick: Fangorn.ButtonEvents._removeEvent
            });
        }
    }
    return buttons.map(function(btn){
                return m('i', { 'data-col' : item.id, 'class' : btn.css, 'data-toggle' : 'tooltip', title : btn.tooltip, 'data-placement': 'bottom',  style : btn.style, 'onclick' : function(event){ btn.onclick.call(self, event, item, col); } },
                    [ m('span', { 'class' : btn.icon}, btn.name) ]);
            });
    
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
    columns.push({
        data : 'name',
        folderIcons : true,
        filter : true,
        custom: _fangornDataverseTitle
    });

    if (this.options.placement === 'project-files') {
        columns.push(
            {
                css: 'action-col',
                filter: false,
                custom: _fangornActionColumn
            },
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
    canDrop: _canDrop
};
