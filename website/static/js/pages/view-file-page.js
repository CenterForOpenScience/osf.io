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
                lazyLoadOnLoad: function(item) {
                    var tb = this;
                    for (var i=0; i < item.children.length; i++) {
                        var child = item.children[i];
                        if (child.data.kind === 'file' && child.data.name === window.contextVars.file.name && child.data.provider === window.contextVars.file.provider) {
                            tb.currentFileId = child.id;
                        }
                    }

                    if (tb.currentFileId) {
                       var index = tb.returnRangeIndex(tb.currentFileId);
                       if (tb.visibleIndexes.indexOf(index) !== -1 ) {
                           var scrollTo = (tb.visibleIndexes.indexOf(index)/ tb.visibleIndexes.length) * 100;
                           $('#tb-tbody').scrollTop(scrollTo);
                       }
                    }
                },
                resolveRows: function (item) {
                    var selectClass = '';
                    if (item.data.kind === 'file' && item.data.name === window.contextVars.file.name && item.data.provider === window.contextVars.file.provider) {
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
        var el = $(this).closest('.panel-toggle');
        el.children('.osf-panel.hidden-xs').hide();
        panelToggle.removeClass('col-md-3').addClass('col-md-1');
        panelExpand.removeClass('col-md-6').addClass('col-md-8');
        el.children('.panel-collapsed').show();

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