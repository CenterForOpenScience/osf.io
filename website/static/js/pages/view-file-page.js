var Fangorn = require('fangorn');
var m = require('mithril');
var nodeApiUrl = window.contextVars.node.urls.api;


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
                    m.render($('#files-search').get(0), tb.options.filterTemplate.call(tb));
                    $('#files-search input[placeholder=Search]').css('width', '95%');
                    $('#files-search input[placeholder=Search]').removeClass('pull-right').addClass('pull-left');
                    $('#toggle-icon').css('margin-top', '5px');
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

                    if (tb.options.folderIndex < tb.options.folderArray.length) {
                        for (var i = 0; i < tree.children.length; i++) {
                            var child = tree.children[i];
                            if (window.contextVars.node.id === child.data.nodeId && child.data.provider === window.contextVars.file.provider && child.data.name === tb.options.folderArray[tb.options.folderIndex]) {
                                tb.options.folderIndex++;
                                if (child.data.kind === 'folder') {
                                    tb.updateFolder(null, child);
                                    tree = child;
                                }
                                else {
                                    tb.currentFileID = child.id;
                                }
                            }
                        }
                    }
                    if (tb.currentFileID) {
                        var index = tb.returnIndex(tb.currentFileID);
                        var visibleIndex = tb.visibleIndexes.indexOf(index);
                        if (visibleIndex !== -1 && visibleIndex > tb.showRange.length - 2) {
                            var scrollTo = visibleIndex * tb.options.rowHeight;
                            $('#tb-tbody').scrollTop(scrollTo);
                        }
                    }
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