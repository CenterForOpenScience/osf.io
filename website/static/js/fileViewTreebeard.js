var Fangorn = require('js/fangorn').Fangorn;
var m = require('mithril');
var $osf = require('js/osfHelpers');

function FileViewTreebeard(data) {

    // Set item.branch to show the branch of the rendered GitHub file instead of the default branch
    var addonRootFolders = data.data[0].children;

    if (window.contextVars.file.provider === 'github' || window.contextVars.file.provider === 'gitlab') {
        for (var i = 0; i < addonRootFolders.length; i++) {
            var item = addonRootFolders[i];
            if ((item.provider === 'github' || item.provider === 'gitlab') && item.isAddonRoot && window.contextVars.file.extra.branch) {
                item.branch = window.contextVars.file.extra.branch;
            }
        }
    }

    var fangornOpts = {
        divID: 'grid',
        filesData: data.data,
        uploads: false,
        showFilter: false,
        title: undefined,
        hideColumnTitles: true,
        multiselect : true,
        placement : 'fileview',
        allowMove : false,
        filterTemplate: function () {
            var tb = this;
            return m('input.pull-left.form-control[placeholder="' + tb.options.filterPlaceholder + '"][type="text"]', {
                style: 'width:100%;display:inline;',
                onkeyup: tb.filter,
                value: tb.filterText()
            });
        },
        xhrconfig: $osf.setXHRAuthorization,
        onload: function(tree) {
            var tb = this;
            Fangorn.DefaultOptions.onload.call(tb, tree);
        },
        ondataload: function () {
            var tb = this;
            var path = '';
            tb.fangornFolderIndex = 0;
            tb.fangornFolderArray = [''];
            if (window.contextVars.file.path) {
                tb.fangornFolderArray = window.contextVars.file.materializedPath.split('/');
                if (tb.fangornFolderArray.length > 1) {
                    tb.fangornFolderArray.splice(0, 1);
                }
            }
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
            if (!this.options.naturalScrollLimit){
                this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
            }
            this.redraw();
        },
        lazyLoadOnLoad: function(tree, event) {
            var tb = this;
            Fangorn.DefaultOptions.lazyLoadOnLoad.call(tb, tree, event);
            Fangorn.Utils.setCurrentFileID.call(tb, tree, window.contextVars.node.id, window.contextVars.file);
            if(!event && tb.isMultiselected(tb.currentFileID)) {
                Fangorn.Utils.scrollToFile.call(tb, tb.currentFileID);
            }
            if (tree.depth > 1) {
                Fangorn.Utils.orderFolder.call(this, tree);
            }
            // if any of the children is the selected add a certain class.
            for (var i = 0; i < tree.children.length; i++){
                var item = tree.children[i];
                if (item.data.kind === 'file' && tb.currentFileID === item.id) {
                    item.css = 'fangorn-selected';
                    tb.multiselected([item]);
                }
            }
        },
        resolveRows: function (item) {
            var tb = this;
            var node = item.parent().parent();
            if(tb.isMultiselected(item.id)) {
                item.css = 'fangorn-selected';
            } else {
                item.css = '';
            }
            if(item.data.permissions && !item.data.permissions.view){
                item.css += ' tb-private-row';
            }
            var defaultColumns = [
                {
                    data: 'name',
                    folderIcons: true,
                    filter: true,
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
