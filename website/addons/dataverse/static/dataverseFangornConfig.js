'use strict';

var m = require('mithril');
var URI = require('URIjs');
var $ = require('jquery');

var Fangorn = require('js/fangorn');
var waterbutler = require('js/waterbutler');

function _uploadUrl(item, file) {
    return waterbutler.buildTreeBeardUpload(item, file);
}

function _downloadEvent(event, item, col) {
    event.stopPropagation();
    window.location = waterbutler.buildTreeBeardDownload(item, {path: item.data.extra.fileId});
}

// Define Fangorn Button Actions
function _fangornActionColumn (item, col) {
    var self = this;
    var buttons = [];

    function dataversePublish(event, item, col) {
        var self = this; // treebeard
        var url = item.data.urls.publish;
        var modalContent = [
            m('h3', 'Publish this dataset?'),
            m('p.m-md', 'By publishing this dataset, all content will be made available through the Harvard Dataverse using their internal privacy settings, regardless of your OSF project settings.'),
            m('p.font-thick.m-md', 'Are you sure you want to publish this dataset?')
        ];
        var modalActions = [
            m('button.btn.btn-default.m-sm', { 'onclick' : function (){ self.modal.dismiss(); }},'Cancel'),
            m('button.btn.btn-primary.m-sm', { 'onclick' : function() { publishDataset(); } }, 'Publish Dataset')
        ];

        this.modal.update(modalContent, modalActions);

        function publishDataset() {
            self.modal.dismiss();
            item.notify.update('Publishing Dataset', 'info', 1, 3000);
            $.osf.putJSON(
                url,
                {}
            ).done(function(data) {
                var modalContent = [
                    m('p.m-md', 'Your dataset has been published. These files will be visible to any user with read-permission until changes to the dataset are made.')
                ];
                var modalActions = [
                    m('button.btn.btn-primary.m-sm', { 'onclick' : function() { self.modal.dismiss(); } }, 'Okay')
                ];
                self.modal.update(modalContent, modalActions);
                item.data.state = 'published';
            }).fail(function(args) {
                var statusCode = args.responseJSON.code;
                var message;
                switch (statusCode) {
                    case 405:
                        message = 'Error: This dataset cannot be published until ' + item.data.name + ' is published.';
                        break;
                    case 409:
                        message = 'This dataset version has already been published.';
                        item.data.state = 'published';
                        break;
                    default:
                        message = 'Error: Something went wrong when attempting to publish your dataset.';
                }

                var modalContent = [
                    m('p.m-md', message)
                ];
                var modalActions = [
                    m('button.btn.btn-primary.m-sm', { 'onclick' : function() { self.modal.dismiss(); } }, 'Okay')
                ];
                self.modal.update(modalContent, modalActions);
            });
        }
    }

    if (item.kind === 'folder' && item.data.addonFullname && item.data.permissions.edit) {
        buttons.push(
            {
                'name' : '',
                'tooltip' : 'Upload file',
                'icon' : 'fa fa-upload',
                'css' : 'fangorn-clickable btn btn-default btn-xs',
                'onclick' : Fangorn.ButtonEvents._uploadEvent
            }
        );
        if (item.data.state === 'draft') {
            buttons.push({
                'name' : '',
                'tooltip' : 'Publish Dataset',
                'icon' : 'fa fa-globe',
                'css' : 'btn btn-primary btn-xs',
                'onclick' : dataversePublish
            })
        }
    } else if (item.kind === 'file') {
        buttons.push({
            name : '',
            'tooltip' : 'Download file',
            icon : 'fa fa-download',
            css : 'btn btn-info btn-xs',
            onclick: _downloadEvent
        });
        if (item.data.permissions.edit) {
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
        if (item.data.state == 'draft') {
            contents.push(
                m('span', {
                    class: 'fa fa-warning text-warning',
                    'data-toggle': 'tooltip',
                    title: 'This data will only be visible to contributors with write-permission until the dataset is published',
                    'data-placement': 'top'

                })
            );
        }
        return m('span', contents);
    } else {
        return m('span',[
            m('dataverse-name', {
                onclick: function() {
                    var redir = new URI(item.data.nodeUrl);
                    window.location = redir
                        .segment('files')
                        .segment(item.data.provider)
                        .segment(item.data.extra.fileId)
                        .toString();
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
    return waterbutler.buildTreeBeardDelete(item, {path: item.data.extra.fileId});
}

function _fangornLazyLoad(item) {
    return waterbutler.buildTreeBeardMetadata(item, {state: item.data.state});
}

function _fangornUploadSuccess(file, item) {
    item.parent().data.state = 'draft';
}

function _canDrop(item) {
    return item.data.provider &&
        item.kind === 'folder' &&
        item.data.permissions.edit
}

Fangorn.config.dataverse = {
    folderIcon: _fangornFolderIcons,
    resolveDeleteUrl: _fangornDeleteUrl,
    resolveRows: _fangornColumns,
    lazyload: _fangornLazyLoad,
    uploadUrl: _uploadUrl,
    uploadSuccess: _fangornUploadSuccess,
    canDrop: _canDrop
};
