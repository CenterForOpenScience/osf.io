var $ = require('jquery');
var m = require('mithril');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
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

        self.reloadFile = function() {
            self.panels.forEach(function(panel) {
                if (panel.reload) {
                    panel.reload();
                }
            });
        };

        self.deleteFile = function() {
            bootbox.confirm({
                title: 'Delete file?',
                message: '<p class="overflow">' +
                        'Are you sure you want to delete <strong>' +
                        self.file.safeName + '</strong>?' +
                    '</p>',
                callback: function(confirm) {
                    if (!confirm) return;
                    $.ajax({
                        type: 'DELETE',
                        url: self.file.urls.delete,
                        beforeSend: $osf.setXHRAuthorization
                    }).done(function() {
                        window.location = self.node.urls.files;
                    }).fail(function() {
                        $osf.growl('Error', 'Could not delete file.');
                    });
                }
            });
        };

        self.downloadFile = function() {
            window.location = self.file.urls.content;
            return false;
        };

        revisionsHeader = m('.row', [
            m('.col-md-6', 'Revisions'),
            m('.col-md-6', [
                m('.pull-right', [
                    m('button.btn.btn-danger.btn-sm', {onclick: self.deleteFile}, 'Delete'),
                    m('button.btn.btn-success.btn-sm', {onclick: self.downloadFile}, 'Download')
                ])
            ])
        ]);

        treeHeader = m('.row', m('.col-md-12', m('#filesSearch')));
        viewHeader = [m('i.fa.fa-eye'), ' View'];
        editHeader = [m('i.fa.fa-pencil-square-o'), ' Edit'];

        self.panels = [
            new Panel('Tree', treeHeader, FileTree, [self.node.urls.api], true),
            new Panel('Edit', editHeader, FileEditor, [self.file.urls.content, self.reloadFile]),
            new Panel('View', viewHeader, FileRenderer, [self.file.urls.render, self.file.urls.sharejs, self.context.editorMeta, self.reloadFile], true),
            new Panel('Revisions', revisionsHeader, FileRevisionsTable, [self.file, self.node], true),
        ];

    },
    view: function(ctrl) {
        return m('.file-view-page', [
            m.component(PanelToggler, m('h3', ctrl.file.name), ctrl.panels)
        ]);
    }
};

module.exports = function(context) {
    return m.component(FileViewPage, context);
};
