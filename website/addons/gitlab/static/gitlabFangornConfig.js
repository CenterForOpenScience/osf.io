'use strict';
/**
 * GitLab FileBrowser configuration module.
 */

var m = require('mithril');
var $ = require('jquery');
var URI = require('URIjs');
var Fangorn = require('js/fangorn').Fangorn;
var waterbutler = require('js/waterbutler');
var $osf = require('js/osfHelpers');

// Cross browser key codes for the Command key
var commandKeys = [224, 17, 91, 93];

function _formatRepoUrl(item, branch) {
    return item.data.urls.repo.substring(0, item.data.urls.repo.indexOf('/tree/') + 6) + branch;
}

function _formatZipUrl(item, branch) {
    return item.data.urls.zip.substring(0, item.data.urls.zip.indexOf('?ref=') + 5) + branch;
}

function _getCurrentBranch(item) {
    var branch;
    if (item.data.branch === undefined) {
        if (item.data.isAddonRoot) {
            branch = item.data.default_branch;
        } else {
            branch = item.data.extra.branch;
        }
    } else {
        branch = item.data.branch;
    }
    return branch;
}

// Define Fangorn Button Actions
var _gitlabItemButtons = {
    view: function (ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var buttons = [];
        function _downloadEvent(event, item, col) {
            event.stopPropagation();
            var branch = _getCurrentBranch(item);
            window.location = waterbutler.buildTreeBeardDownload(item, {branch: branch});
        }
        // Download Zip File
        if (item.kind === 'folder') {
            var branchArray = [];
            if (item.data.branches) {
                item.data.branch = _getCurrentBranch(item);
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
                if (item.data.addonFullname) {
                    var branch = _getCurrentBranch(item);

                    buttons.push(
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                window.location = _formatZipUrl(item, branch);
                            },
                            icon: 'fa fa-download',
                            className: 'text-primary'
                        }, 'Download'),
                        m.component(Fangorn.Components.button, {
                            onclick: function (event) {
                                window.open(_formatRepoUrl(item, branch), '_blank');
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
            if (item.data.permissions && item.data.permissions.view && !item.data.permissions.private) {
                buttons.push(
                    m('a.text-info.fangorn-toolbar-icon', {href: item.data.extra.webView}, [
                        m('i.fa.fa-external-link'),
                        m('span', 'View on GitLab')
                    ])
                );
            }
        }

        return m('span', buttons); // Tell fangorn this function is used.
    }
};

function changeBranch(item, ref){
    item.data.branch = ref;
    this.updateFolder(null, item);
}

function _resolveLazyLoad(item) {
    var branch = _getCurrentBranch(item);
    return waterbutler.buildTreeBeardMetadata(item, {ref: branch});
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
    var branch = _getCurrentBranch(item);
    var fileurl = new URI(item.data.nodeUrl)
        .segment('files')
        .segment(item.data.provider)
        .segment(item.data.path.substring(1))
        .search({branch: branch})
        .toString();
    if(commandKeys.indexOf(tb.pressedKey) !== -1) {
        window.open(fileurl, '_blank');
    } else {
        window.open(fileurl, '_self');
    }
}

function _fangornGitLabTitle(item, col)  {
    var tb = this;
    if (item.data.isAddonRoot && item.connected === false) { // as opposed to undefined, avoids unnecessary setting of this value
        return Fangorn.Utils.connectCheckTemplate.call(this, item);
    }

    if (item.data.addonFullname) {
        var urlParams = $osf.urlParams();

        if (!item.data.branch && urlParams.branch) {
            item.data.branch = urlParams.branch;
        }
        var branch = _getCurrentBranch(item);

        return m('span',[
            m('gitlab-name', item.data.name + ' (' + branch + ')')
        ]);
    } else {
        if (item.kind === 'file' && item.data.permissions.view) {
            return m('span',[
                m('gitlab-name.fg-file-links', {
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
        custom : _fangornGitLabTitle
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
Fangorn.config.gitlab = {
    // Handle changing the branch select
    lazyload: _resolveLazyLoad,
    resolveRows: _fangornColumns,
    folderIcon: _fangornFolderIcons,
    onUploadComplete: _fangornUploadComplete,
    lazyLoadOnLoad: _fangornLazyLoadOnLoad,
    uploadSuccess: _fangornUploadSuccess,
    itemButtons: _gitlabItemButtons,
};
