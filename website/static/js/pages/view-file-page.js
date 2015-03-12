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
                    return [];
                },
                resolveRows: function (item) {
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
        });
});