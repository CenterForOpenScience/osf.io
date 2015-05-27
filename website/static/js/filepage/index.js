var $ = require('jquery');
var m = require('mithril');
var waterbutler = require('js/waterbutler');

// Local requires
var utils = require('./util.js');
var FileTree = require('./tree.js');
var FileRenderer = require('./render.js');
var FileEditor = require('./editor.js');
var FileRevisionsTable = require('./revisions.js');

//Sanity
var Panel = utils.Panel;
var PanelToggler = utils.PanelToggler;


var FileViewPage = {
    controller: function(context) {
        var self = this;
        self.context = context;
        self.file = self.context.file;
        self.node = self.context.node;
        self.editorMeta = self.context.editor;

        $.extend(self.file.urls, {
            delete: waterbutler.buildDeleteUrl(self.file.path, self.file.provider, self.node.id),
            content: waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id),
            metadata: waterbutler.buildMetadataUrl(self.file.path, self.file.provider, self.node.id),
            revisions: waterbutler.buildRevisionsUrl(self.file.path, self.file.provider, self.node.id)
        });

        self.reloadFile = function() {
            self.panels.forEach(function(panel) {
                if (panel.reload) {
                    panel.reload();
                }
            });
        };

        self.panels = [
            Panel('Tree', FileTree, [self.node.urls.api], true),
            Panel('Edit', FileEditor, [self.file.urls.content, self.file.urls.sharejs, self.editorMeta, self.reloadFile], true),
            Panel('View', FileRenderer, [self.file.urls.render, self.file.urls.sharejs, self.context.editorMeta, self.reloadFile], true),
            Panel('Revisions', FileRevisionsTable, [self.file, self.node], true),
        ];

    },
    view: function(ctrl) {
        return m('.file-view-page', [
            m.component(PanelToggler, ctrl.panels)
        ]);
    }
};

module.exports = function(context) {
    return m.component(FileViewPage, context);
};
