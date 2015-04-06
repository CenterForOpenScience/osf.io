var Fangorn = require('js/fangorn');
var m = require('mithril');

function FileViewTreebeard(data) {

    // Set item.branch to show the branch of the rendered GitHub file instead of the default branch
    var addonRootFolders = data['data'][0].children;
    for (var i=0; i < addonRootFolders.length; i++) {
        var item = addonRootFolders[i];
        if (item.provider === 'github' && item.isAddonRoot && window.contextVars.file.extra.branch) {
            item.branch = window.contextVars.file.extra.branch;
        }
    }

    var fangornOpts = {
    divID: 'grid',
    filesData: data.data,
    uploads: false,
    showFilter: false,
    title: undefined,
    hideColumnTitles: true,
    onload: function(tree) {
        var tb = this;
        Fangorn.DefaultOptions.onload.call(tb, tree);
        $('.osf-panel-header.osf-panel-header-flex').show();
    },
    ondataload: function () {
        var tb = this;
        tb.options.folderIndex = 0;
        if (window.contextVars.file.provider === 'figshare') {
            tb.options.folderArray = [window.contextVars.file.name]
        } else if (window.contextVars.file.path) {
            window.contextVars.file.path = decodeURIComponent(window.contextVars.file.path);
            tb.options.folderArray = window.contextVars.file.path.split("/");
            if (tb.options.folderArray.length > 1) {
                tb.options.folderArray.splice(0, 1);
            }
        } else {
            tb.options.folderArray = [''];
        }
        m.render($('#filesSearch').get(0), tb.options.filterTemplate.call(tb));
        $('#filesSearch input[placeholder=Search]').css('width', '95%');
        $('#filesSearch input[placeholder=Search]').removeClass('pull-right').addClass('pull-left');
        $('#toggleIcon').css('margin-top', '5px');
    },
    columnTitles: function () {
        return [{
            title: 'Name',
            width: '100%'
        }];
    },
    ontogglefolder : function (tree) {
        Fangorn.DefaultOptions.ontogglefolder.call(this, tree);
        var containerHeight = this.select('#tb-tbody').height();
        this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
        this.redraw();
    },
    lazyLoadOnLoad: function(tree) {
        var tb = this;
        Fangorn.DefaultOptions.lazyLoadOnLoad.call(tb, tree);
        Fangorn.Utils.findCurrentFileID.call(tb, tree, window.contextVars.node.id, window.contextVars.file);
        Fangorn.Utils.scrollToFile.call(tb, tb.currentFileID);
    },
    resolveRows: function (item) {
        var selectClass = '';
        var tb = this;
        var node = item.parent().parent();
        if (item.data.kind === 'file' && tb.currentFileID === item.id) {
            selectClass = 'fangorn-hover';
        }

        var defaultColumns = [
            {
                data: 'name',
                folderIcons: true,
                filter: true,
                css: selectClass,
                custom: Fangorn.DefaultColumns._fangornTitleColumn
            }
        ];

        if (item.parentID) {
            item.data.permissions = item.data.permissions || item.parent().data.permissions;
            if (item.data.kind === 'folder') {
                item.data.accept = item.data.accept || item.parent().data.accept;
            }
        }

        if (item.data.tmpID) {
            defaultColumns = [
                {
                    data: 'name',  // Data field name
                    folderIcons: true,
                    filter: true,
                    custom: function () {
                        return m('span.text-muted', 'Uploading ' + item.data.name + '...');
                    }
                }
            ];
        }

        var configOption = Fangorn.Utils.resolveconfigOption.call(this, item, 'resolveRows', [item]);
        return configOption || defaultColumns;
    }
    };
    var filebrowser = new Fangorn(fangornOpts);
}


module.exports = FileViewTreebeard;