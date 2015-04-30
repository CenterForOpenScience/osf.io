'use strict';
/**
 * Github FileBrowser configuration module.
 */
var m = require('mithril');
var URI = require('URIjs');

var Fangorn = require('js/fangorn');
var waterbutler = require('js/waterbutler');


function _uploadUrl(item, file) {
    return waterbutler.buildTreeBeardUpload(item, file, {branch: item.data.branch});
}

// TODO: Refactor, repeating from core function too much
function _removeEvent (event, items) {
    var tb = this;
    function cancelDelete() {
        tb.modal.dismiss();
    }

    function runDelete (item) {
        $('.tb-modal-footer .btn-success').html('<i> Deleting...</i>').attr('disabled', 'disabled');
        // delete from server, if successful delete from view
        $.ajax({
            url: waterbutler.buildTreeBeardDelete(item, {branch: item.data.branch, sha: item.data.extra.fileSha}),
            type : 'DELETE'
        })
        .done(function(data) {
            // delete view
            tb.deleteNode(item.parentID, item.id);
            Fangorn.Utils.resetToolbar.call(tb);
            tb.modal.dismiss();
        })
        .fail(function(data){
            tb.modal.dismiss();
            Fangorn.Utils.resetToolbar.call(tb);
            item.notify.update('Delete failed.', 'danger', undefined, 3000);
        });
    }

    function runDeleteMultiple(items){
        items.forEach(function(item){
            runDelete(item);
        });
        this.options.iconState.generalIcons.deleteMultiple.on = false;
    }

    // If there is only one item being deleted, don't complicate the issue:
    if(items.length === 1) {
        var parent = items[0].parent();
        var mithrilContentSingle = m('div', [
            m('h3.break-word', 'Delete "' + items[0].data.name + '"'),
            m('p', 'This action is irreversible.'),
            parent.children.length < 2 ? m('p', 'If a folder in Github has no children it will automatically be removed.') : ''
        ]);
        var mithrilButtonsSingle = m('div', [
            m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() { cancelDelete(); } }, 'Cancel'),
            m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDelete(items[0]); }  }, 'OK')
        ]);
        // This is already being checked before this step but will keep this edit permission check
        if(items[0].data.permissions.edit){
            tb.modal.update(mithrilContentSingle, mithrilButtonsSingle);
        }
    } else {
        // Check if all items can be deleted
        var canDelete = true;
        var deleteList = [];
        var noDeleteList = [];
        var mithrilContentMultiple;
        var mithrilButtonsMultiple;
        items.forEach(function(item, index, arr){
            if(!item.data.permissions.edit){
                canDelete = false;
                noDeleteList.push(item);
            } else {
                deleteList.push(item);
            }
        });
        // If all items can be deleted      
        if(canDelete){
            mithrilContentMultiple = m('div', [
                    m('h3.break-word', 'Delete multiple files?'),
                    m('p', 'This action is irreversible.'),
                    deleteList.map(function(item){
                        return m('.fangorn-canDelete.text-success', item.data.name);
                    })
                ]);
            mithrilButtonsMultiple =  m('div', [
                    m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() { cancelDelete(); } }, 'Cancel'),
                    m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); }  }, 'Delete All')
                ]);        
        } else {
            mithrilContentMultiple = m('div', [
                    m('h3.break-word', 'Delete multiple files?'),
                    m('p', 'Some of these files can\'t be deleted but you can delete the ones highlighted with green. This action is irreversible.'),
                    deleteList.map(function(n){
                        return m('.fangorn-canDelete.text-success', n.data.name);
                    }),
                    noDeleteList.map(function(n){
                        return m('.fangorn-noDelete.text-warning', n.data.name);
                    })
                ]);            
            mithrilButtonsMultiple =  m('div', [
                    m('span.tb-modal-btn', { 'class' : 'text-primary', onclick : function() { cancelDelete(); } }, 'Cancel'),
                    m('span.tb-modal-btn', { 'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); }  }, 'Delete Some')
                ]);    
        }
        tb.modal.update(mithrilContentMultiple, mithrilButtonsMultiple); 
    }

    return true; // Let fangorn know this config option was used. 
}


// Define Fangorn Button Actions
function _githubDefineToolbar (item){
    var self = this;
    var buttons = [];

    function _downloadEvent (event, item, col) {
        event.stopPropagation();
        window.location = waterbutler.buildTreeBeardDownload(item, {fileSha: item.data.extra.fileSha});
    }

    // Download Zip File
    if (item.kind === 'folder') {
    var branchArray = [];
    if (item.data.branches) {
        item.data.branch = item.data.branch || item.data.defaultBranch;
        for (var i = 0; i < item.data.branches.length; i++) {
            var selected = item.data.branches[i] === item.data.branch ? 'selected' : '';
            branchArray.push(m('option', {selected : selected, value:item.data.branches[i]}, item.data.branches[i]));
        }
    }


        // If File and FileRead are not defined dropzone is not supported and neither is uploads
        if (window.File && window.FileReader && item.data.permissions && item.data.permissions.edit) {
            buttons.push({ name : 'uploadFiles', template : function(){
                return m('.fangorn-toolbar-icon.text-success', {
                        onclick : function(event) { Fangorn.ButtonEvents._uploadEvent.call(self, event, item); } 
                    },[
                    m('i.fa.fa-upload'),
                    m('span.hidden-xs','Upload')
                ]);
            }},
            { name : 'createFolder', template : function(){
                return m('.fangorn-toolbar-icon.text-info', {
                        onclick : function(event) { Fangorn.ButtonEvents.createFolder.call(self, event, item) } 
                    },[
                    m('i.fa.fa-plus'),
                    m('span.hidden-xs','Create Folder')
                ]);
            }});
        }
        if (item.data.addonFullname) {
            buttons.push(
                { name : 'downloadFile', template : function(){
                    return m('.fangorn-toolbar-icon.text-info', {
                            onclick : function(event) { window.location = item.data.urls.zip; } 
                        },[
                        m('i.fa.fa-download'),
                        m('span.hidden-xs','Download')
                    ]);
                }},
                { name : 'gotoRepo', template : function(){
                    return m('.fangorn-toolbar-icon.text-info', {
                            onclick : function(event) { window.open(item.data.urls.repo, '_blank');} 
                        },[
                        m('i.fa.fa-external-link'),
                        m('span.hidden-xs','Open')
                    ]);
                }},
                {
                    name : 'changeBranch', template : function(){
                        return m('.fangorn-toolbar-icon.text-info', 
                            [ 
                               m('span.hidden-xs','Branch :'),
                               m('select[name=branch-selector].no-border', { onchange: function(ev) { changeBranch.call(self, item, ev.target.value ); }, 'data-toggle' : 'tooltip', title : 'Change Branch', 'data-placement': 'bottom' }, branchArray)
                            ]
                        );
                    }
                }
            );
        }
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

        if (item.data.permissions && item.data.permissions.edit) {
            buttons.push(
                { name : 'deleteFile', template : function(){
                    return m('.fangorn-toolbar-icon.text-danger', {
                            onclick : function(event) { _removeEvent.call(self, event, [item]); } 
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

function changeBranch(item, ref){
    item.data.branch = ref;
    this.updateFolder(null, item);
}

function _resolveLazyLoad(item) {
    return waterbutler.buildTreeBeardMetadata(item, {ref: item.data.branch});
}

function _fangornLazyLoadOnLoad (tree, event) {
    var tb = this;
    tree.children.forEach(function(item) {
        Fangorn.Utils.inheritFromParent(item, tree, ['branch']);
    });
    Fangorn.Utils.setCurrentFileID.call(tb, tree, window.contextVars.node.id, window.contextVars.file);
    if(!event){
        Fangorn.Utils.scrollToFile.call(tb, tb.currentFileID);
    }
}

function _fangornGithubTitle(item, col)  {
    var tb = this;
    if (item.data.addonFullname) {
        return m('span',[
            m('github-name', item.data.name + ' (' + item.data.branch + ')')
        ]);
    } else {
        if (item.kind === 'file' && item.data.permissions.view) {
            return m('span',[
                m('github-name', {
                    ondblclick: function() {
                        var redir = new URI(item.data.nodeUrl);
                        window.location = new URI(item.data.nodeUrl)
                            .segment('files')
                            .segment(item.data.provider)
                            .segment(item.data.path.substring(1))
                            .search({branch: item.data.branch})
                            .toString();
                    },
                    'data-toggle': 'tooltip',
                    title: 'View file',
                    'data-placement': 'bottom'
                }, item.data.name)]);
        } else {
            return m('span', item.data.name);
        }
    }
}


function _fangornColumns (item) {
    var tb = this;
    var selectClass = '';
    var node = item.parent().parent();
    if (item.data.kind === 'file' && tb.currentFileID === item.id) {
        selectClass = 'fangorn-hover';
    }

    var columns = [];
    
    if(tb.options.placement !== 'fileview'){  // File view page structure is slightly different. 
        columns.push({
            data : null,
            folderIcons: false,
            filter : false,
            custom : function(){
                if(this.isMultiselected(item.id)) {
                    return m('div.fangorn-select-toggle', { style : 'color: white'},m('i.fa.fa-check-square-o'));
                }
                return m('div.fangorn-select-toggle', m('i.fa.fa-square-o'));
            }
        });        
    }


    columns.push({
        data : 'name',
        folderIcons : true,
        filter: true,
        css: selectClass,
        custom : _fangornGithubTitle
    });

    if(tb.options.placement === 'project-files') {
        columns.push(
        {
            data  : 'downloads',
            filter : false,
            css : ''
        });
    }
    return columns;
}

function _fangornFolderIcons(item){
    if(item.data.iconUrl){
        return m('img',{src:item.data.iconUrl, style:{width:'16px', height:'auto'}}, ' ');
    }
    return undefined;
}

function _fangornUploadComplete(item){
    var index = this.returnIndex(item.id);
}

function _fangornUploadSuccess(file, item, response) {
    if (response) {
        response.branch = item.parent().data.branch;
    }
}

// Register configuration
Fangorn.config.github = {
    // Handle changing the branch select
    uploadUrl: _uploadUrl,
    lazyload: _resolveLazyLoad,
    resolveRows: _fangornColumns,
    folderIcon: _fangornFolderIcons,
    onUploadComplete: _fangornUploadComplete,
    lazyLoadOnLoad: _fangornLazyLoadOnLoad,
    uploadSuccess: _fangornUploadSuccess,
    defineToolbar: _githubDefineToolbar,
    removeEvent : _removeEvent

};
