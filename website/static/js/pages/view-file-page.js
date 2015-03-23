var Fangorn = require('fangorn');

var FileRenderer = require('../filerenderer.js');
var FileRevisions = require('../fileRevisions.js');

if (window.contextVars.renderURL !== undefined) {
    FileRenderer.start(window.contextVars.renderURL, '#fileRendered');
}

new FileRevisions(
    '#fileRevisions',
    window.contextVars.node,
    window.contextVars.file,
    window.contextVars.currentUser.canEdit
);

$(document).ready(function() {
    // Treebeard Files view
    $.ajax({
        url: nodeApiUrl + 'files/grid/'
    })
        .done(function (data) {
            var fangornOpts = {
                divID: 'grid',
                filesData: data.data,
                uploads: false,
                showFilter: false,
                title: undefined,
                hideColumnTitles: true,
                columnTitles: function () {
                    return [{
                        title: 'Name',
                        width: '100%'
                    }];
                },
                ontogglefolder : function (tree){
                    Fangorn.DefaultOptions.ontogglefolder.call(this, tree);
                    var containerHeight = this.select('#tb-tbody').height();
                    this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
                    this.redraw();
                },
                lazyLoadOnLoad: function(tree) {
                    Fangorn.DefaultOptions.lazyLoadOnLoad.call(this, tree);
                    var tb = this;
                    var node = tree.parent();
                    for (var i=0; i < tree.children.length; i++) {
                        var child = tree.children[i];
                        if (child.data.kind === 'file' && window.contextVars.node.id === node.data.nodeID && child.data.name === window.contextVars.file.name && child.data.provider === window.contextVars.file.provider) {
                            tb.currentFileId = child.id;
                        }
                    }

                    if (tb.currentFileId) {
                        var index = tb.returnIndex(tb.currentFileId);
                        var visibleIndex = tb.visibleIndexes.indexOf(index);
                        if (visibleIndex !== -1 && visibleIndex > tb.showRange.length - 2) {
                            var scrollTo = visibleIndex * tb.options.rowHeight;
                            $('#tb-tbody').scrollTop(scrollTo);
                        }
                    }
                },
                resolveRows: function (item) {
                    var selectClass = '';
                    var node = item.parent().parent();
                    if (item.data.kind === 'file' && window.contextVars.node.id === node.data.nodeID && item.data.name === window.contextVars.file.name && item.data.provider === window.contextVars.file.provider) {
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
        });

    var panelToggle = $('.panel-toggle');
    var panelExpand = $('.panel-expand');
    $('.panel-collapse').on('click', function () {
        var panelHeight = $('.osf-panel.hidden-xs').height();
        var el = $(this).closest('.panel-toggle');
        el.children('.osf-panel.hidden-xs').hide();
        panelToggle.removeClass('col-md-3').addClass('col-md-1');
        panelExpand.removeClass('col-md-6').addClass('col-md-8');
        el.children('.panel-collapsed').show();
        el.children('.panel-collapsed').css('height', panelHeight);
    });
    $('.panel-collapsed .osf-panel-header').on('click', function () {
        var el = $(this).parent();
        var toggle = el.closest('.panel-toggle');
        toggle.children('.osf-panel').show();
        el.hide();
        panelToggle.removeClass('col-md-1').addClass('col-md-3');
        panelExpand.removeClass('col-md-8').addClass('col-md-6');
    });
});