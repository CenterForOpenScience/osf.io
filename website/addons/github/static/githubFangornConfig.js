'use strict';
/**
 * Github FileBrowser configuration module.
 */

var m = require('mithril');
var $ = require('jquery');
var URI = require('URIjs');
var Fangorn = require('js/fangorn').Fangorn;
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

// Cross browser key codes for the Command key
var commandKeys = [224, 17, 91, 93];

function _uploadUrl(item, file) {
    // WB v1 update syntax is PUT <file_path>?kind=file
    // WB v1 upload syntax is PUT <parent_path>/?kind=file&name=<filename>
    // If upload target file name already exists don't pass file.name.  WB v1 rejects updates that
    // include a filename.
    var updateUrl;
    $.each(item.children, function( index, value ) {
        if (file.name === value.data.name) {
            updateUrl = waterbutler.buildTreeBeardUpload(value, {branch: value.data.branch});
            return false;
        }
    });
    return updateUrl || waterbutler.buildTreeBeardUpload(item, {name: file.name, branch: item.data.branch});
}

function _removeEvent (event, items) {
    var tb = this;
    function cancelDelete() {
        tb.modal.dismiss();
    }

    function runDelete (item) {
        // delete from server, if successful delete from view
        tb.select('.modal-footer .btn-danger').html('<i> Deleting...</i>').removeClass('btn-danger').addClass('btn-default disabled');

        $.ajax({
            url: waterbutler.buildTreeBeardDelete(item, {branch: item.data.branch, sha: item.data.extra.fileSha}),
            type : 'DELETE',
            beforeSend: $osf.setXHRAuthorization
        }).done(function (data) {
                // delete view
                tb.deleteNode(item.parentID, item.id);
                tb.modal.dismiss();
                tb.clearMultiselect();
        }).fail(function (data) {
                tb.modal.dismiss();
                Fangorn.Utils.dismissToolbar.call(tb);
                item.notify.update('Delete failed.', 'danger', undefined, 3000);
                tb.clearMultiselect();
        });
    }

    function runDeleteMultiple(items){
        items.forEach(function(item){
            runDelete(item);
        });
    }

    function doDelete() {
        var folder = items[0];
        if (folder.data.permissions.edit) {
            var mithrilContent = m('div', [
                    m('p.text-danger', 'This folder and ALL its contents will be deleted. This action is irreversible.')
                ]);
            var mithrilButtons = m('div', [
                    m('span.btn.btn-default', { onclick : function() { cancelDelete.call(tb); } }, 'Cancel'),
                    m('span.btn.btn-danger', {  onclick : function() { runDelete(folder); }  }, 'Delete')
                ]);
            tb.modal.update(mithrilContent, mithrilButtons, m('h3.break-word.modal-title', 'Delete "' + folder.data.name+ '"?'));
        } else {
            folder.notify.update('You don\'t have permission to delete this file.', 'info', undefined, 3000);
        }
    }

    // If there is only one item being deleted, don't complicate the issue:
    if(items.length === 1) {
        if(items[0].kind !== 'folder') {
            var parent = items[0].parent();
            var mithrilContentSingle = m('div', [
                m('p', 'This action is irreversible.'),
                parent.children.length < 2 ? m('p', 'If a folder in Github has no children it will automatically be removed.') : ''
            ]);
            var mithrilButtonsSingle = m('div', [
                m('span.btn.btn-default', {
                    onclick: function () {
                        cancelDelete();
                    }
                }, 'Cancel'),
                m('span.btn.btn-danger', {
                    onclick: function () {
                        runDelete(items[0]);
                    }
                }, 'Delete')
            ]);
            // This is already being checked before this step but will keep this edit permission check
            if (items[0].data.permissions.edit) {
                tb.modal.update(mithrilContentSingle, mithrilButtonsSingle, m('h3.break-word.modal-title', 'Delete "' + items[0].data.name + '"?'));
            }
        }
        if(items[0].kind === 'folder') {
            if (!items[0].open) {
                tb.updateFolder(null, items[0], doDelete);
            } else {
                doDelete();
            }
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
                    m('p.text-danger', 'This action is irreversible.'),
                    deleteList.map(function(item){
                        return m('.fangorn-canDelete.text-success', item.data.name);
                    })
                ]);
            mithrilButtonsMultiple =  m('div', [
                    m('span.btn.btn-default', { 'class' : 'text-default', onclick : function() { cancelDelete(); } }, 'Cancel'),
                    m('span.btn.btn-danger', {  'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); }  }, 'Delete All')
                ]);
        } else {
            mithrilContentMultiple = m('div', [
                    m('p', 'Some of these files can\'t be deleted but you can delete the ones highlighted with green. This action is irreversible.'),
                    deleteList.map(function(n){
                        return m('.fangorn-canDelete.text-success', n.data.name);
                    }),
                    noDeleteList.map(function(n){
                        return m('.fangorn-noDelete.text-warning', n.data.name);
                    })
                ]);
            mithrilButtonsMultiple =  m('div', [
                    m('span.btn.btn-default', { 'class' : 'text-default', onclick : function() { cancelDelete(); } }, 'Cancel'),
                    m('span.btn.btn-danger', { 'class' : 'text-danger', onclick : function() { runDeleteMultiple.call(tb, deleteList); }  }, 'Delete Some')
                ]);
        }
        tb.modal.update(mithrilContentMultiple, mithrilButtonsMultiple, m('h3.break-word.modal-title', 'Delete multiple files?'));
    }

    return true; // Let fangorn know this config option was used.
}


// Define Fangorn Button Actions
var _githubItemButtons = {
    view: function (ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var buttons = [];
        function _downloadEvent(event, item, col) {
            event.stopPropagation();
            window.location = waterbutler.buildTreeBeardDownload(item, {fileSha: item.data.extra.fileSha, branch: item.data.branch});
        }
        // Download Zip File
        if (item.kind === 'folder') {
            var branchArray = [];
            if (item.data.branches) {
                item.data.branch = item.data.branch || item.data.defaultBranch;
                for (var i = 0; i < item.data.branches.length; i++) {
                    var selected = item.data.branches[i] === item.data.branch ? 'selected' : '';
                    branchArray.push(m('option', {
                        selected: selected,
                        value: item.data.branches[i]
                    }, item.data.branches[i]));
                }
            }
            if (item.data.addonFullname) {
                buttons.push(
                    m.component(Fangorn.Components.dropdown, {
                        'label': 'Branch: ',
                        onchange: function (event) {
                            changeBranch.call(tb, item, event.target.value);
                        },
                        icon: 'fa fa-external-link',
                        className: 'text-info'
                    }, branchArray)
                );
            }
            if (tb.options.placement !== 'fileview') {
                // If File and FileRead are not defined dropzone is not supported and neither is uploads
                if (window.File && window.FileReader && item.data.permissions && item.data.permissions.edit) {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                Fangorn.ButtonEvents._uploadEvent.call(tb, event, item);
                            },
                            icon: 'fa fa-upload',
                            className: 'text-success'
                        }, 'Upload'),
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                tb.toolbarMode(Fangorn.Components.toolbarModes.ADDFOLDER);
                            },
                            icon: 'fa fa-plus',
                            className: 'text-success'
                        }, 'Create Folder')
                    );
                    if(!item.data.isAddonRoot){
                        buttons.push(m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                _removeEvent.call(tb, event, [item]);
                            },
                            icon: 'fa fa-trash',
                            className: 'text-danger'
                        }, 'Delete Folder'));
                    }
                }
                if (item.data.addonFullname) {
                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                window.location = waterbutler.buildTreeBeardDownloadZip(item, {'branch': item.data.branch});
                            },
                            icon: 'fa fa-download',
                            className: 'text-primary'
                        }, 'Download'),
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                window.open(item.data.urls.repo, '_blank');
                            },
                            icon: 'fa fa-external-link',
                            className: 'text-info'
                        }, 'Open')
                    );
                }
            }
        } else if (item.kind === 'file' && tb.options.placement !== 'fileview') {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        _downloadEvent.call(tb, event, item);
                    },
                    icon: 'fa fa-download',
                    className: 'text-primary'
                }, 'Download')
            );
            if (item.data.permissions && item.data.permissions.view) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function(event) {
                            gotoFile.call(tb, item);
                        },
                        icon: 'fa fa-file-o',
                        className : 'text-info'
                    }, 'View'));
            }
            if (item.data.permissions && item.data.permissions.edit) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            _removeEvent.call(tb, event, [item]);
                        },
                        icon: 'fa fa-trash',
                        className: 'text-danger'
                    }, 'Delete')
                );
            }
            if (item.data.permissions && item.data.permissions.view && !item.data.permissions.private) {
                buttons.push(
                    m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                        m('i.fa.fa-external-link'),
                        m('span', 'View on GitHub')
                    ])
                );
            }
        }

        if(item.data.provider && !item.data.isAddonRoot && item.data.permissions && item.data.permissions.edit && tb.options.placement !== 'fileview') {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function() {
                        tb.toolbarMode(Fangorn.Components.toolbarModes.RENAME);
                    },
                    icon: 'fa fa-pencil',
                    className : 'text-info'
                }, 'Rename')
            );
        }

        return m('span', buttons); // Tell fangorn this function is used.
    }
};

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
    if(!event && tb.isMultiselected(tb.currentFileID)){
        Fangorn.Utils.scrollToFile.call(tb, tb.currentFileID);
    }
}

function gotoFile (item) {
    var tb = this;
    var fileurl = new URI(item.data.nodeUrl)
        .segment('files')
        .segment(item.data.provider)
        .segment(item.data.path.substring(1))
        .search({branch: item.data.branch})
        .toString();
    if(commandKeys.indexOf(tb.pressedKey) !== -1) {
        window.open(fileurl, '_blank');
    } else {
        window.open(fileurl, '_self');
    }
}

function _fangornGithubTitle(item, col)  {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) { // as opposed to undefined, avoids unnecessary setting of this value
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }

    if (item.data.addonFullname) {
        var urlParams = $osf.urlParams();

        if (!item.data.branch && urlParams.branch) {
            item.data.branch = urlParams.branch;
        }
        var branch = item.data.branch || item.data.defaultBranch;

        return m('span',[
            m('github-name', item.data.name + ' (' + branch + ')')
        ]);
    } else {
        if (item.kind === 'file' && item.data.permissions.view) {
            return m('span',[
                m('github-name.fg-file-links', {
                    onclick: function() {
                        gotoFile.call(tb, item);
                    }
                }, item.data.name)]);
        } else {
            return m('span', item.data.name);
        }
    }
}

function _fangornColumns (item) {
    var tb = this;
    var node = item.parent().parent();
    var columns = [];
    columns.push({
        data : 'name',
        folderIcons : true,
        filter: true,
        custom : _fangornGithubTitle
    });

    if(tb.options.placement === 'project-files') {
        columns.push(
        {
            data  : 'size',
            sortInclude : false,
            filter : false,
            custom : function() {return item.data.size ? $osf.humanFileSize(item.data.size, true) : '';}
        });
        columns.push(
        {
            data  : 'downloads',
            sortInclude : false,
            filter : false,
            custom : function() {return m('');}
        });
        columns.push({
            data: 'version',
            filter: false,
            sortInclude : false,
            custom: function() {return m('');}
        });
    }
    if(tb.options.placement !== 'fileview') {
        columns.push({
            data : 'modified',
            filter: false,
            custom : function() {return m('');}
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
    itemButtons: _githubItemButtons,
    removeEvent : _removeEvent
};
