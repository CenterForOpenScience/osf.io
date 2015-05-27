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

        $.extend(self.file.urls, {
            delete: waterbutler.buildDeleteUrl(self.file.path, self.file.provider, self.node.id),
            content: waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id),
            metadata: waterbutler.buildMetadataUrl(self.file.path, self.file.provider, self.node.id),
            revisions: waterbutler.buildRevisionsUrl(self.file.path, self.file.provider, self.node.id)
        });

        self.panels = [
            Panel('Tree', FileTree),
            Panel('Edit', FileEditor),
            Panel('View', FileRenderer, [self.file.urls.render], true),
            Panel('Revisions', FileRevisionsTable, [self.file], true),
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
