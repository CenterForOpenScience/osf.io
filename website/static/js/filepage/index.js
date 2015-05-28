var $ = require('jquery');
var m = require('mithril');
var mime = require('mime-types');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

// Local requires
var utils = require('./util.js');
var FileRenderer = require('./render.js');
var FileEditor = require('./editor.js');
var FileRevisionsTable = require('./revisions.js');

//Sanity
var Panel = utils.Panel;
var PanelToggler = utils.PanelToggler;


var EDITORS = {'text': FileEditor};

window.m = m;


var FileViewPage = {
    controller: function(context) {
        var self = this;
        self.context = context;
        self.canEdit = m.prop(false);
        self.file = self.context.file;
        self.node = self.context.node;
        self.editorMeta = self.context.editor;

        $.extend(self.file.urls, {
            delete: waterbutler.buildDeleteUrl(self.file.path, self.file.provider, self.node.id),
            metadata: waterbutler.buildMetadataUrl(self.file.path, self.file.provider, self.node.id),
            revisions: waterbutler.buildRevisionsUrl(self.file.path, self.file.provider, self.node.id),
            content: waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id, {accept_url: false}),
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
                m('.pull-right.btn-group.btn-group-sm', [
                    m('button.btn.btn-danger', {onclick: self.deleteFile}, 'Delete'),
                    m('button.btn.btn-success', {
                        onclick: self.downloadFile,
                        href: '?' + $.param($.extend(true, {}, $osf.urlParams(), {download: true}))
                    }, 'Download')
                ])
            ])
        ]);

        viewHeader = [m('i.fa.fa-eye'), ' View'];
        editHeader = [m('i.fa.fa-pencil-square-o'), ' Edit'];

        //crappy hack to delay creation of the editor
        //until we know this is the current file revsion
        self.enableEditing = function() {
            var fileType = mime.lookup(self.file.name);
            if (self.file.size < 1048576 && fileType) { //May return false
                editor = EDITORS[fileType.split('/')[0]];
                if (editor) {
                    var p = Panel('Edit', editHeader, editor, [self.file.urls.content, self.file.urls.sharejs, self.editorMeta, self.reloadFile], true);
                    // Splicing breaks mithrils caching :shrug:
                    // self.panels.splice(1, 0, p);
                    self.panels.push(p);
                }
            }
        };

        self.panels = [
            Panel('View', viewHeader, FileRenderer, [self.file.urls.render], true),
            Panel('Revisions', revisionsHeader, FileRevisionsTable, [self.file, self.node, self.enableEditing]),
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
