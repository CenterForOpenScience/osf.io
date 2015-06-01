var $ = require('jquery');
var m = require('mithril');
var pym = require('pym.js');
var mime = require('js/mime');
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
            content: waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id, {accept_url: false, mode: 'render'}),
        });

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

        self.shareJSObservables = {
            activeUsers: m.prop([]),
            status: m.prop('connecting'),
            userId: self.context.currentUser.id
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

        editHeader = function() {
            return m('.row', [
                m('.col-md-3', [
                    m('i.fa.fa-pencil-square-o'),
                    ' Edit',
                ]),
                m('.col-md-6', [
                    m('', [
                        m('.progress.progress-no-margin.pointer', {
                            'data-toggle': 'modal',
                            'data-target': '#' + self.shareJSObservables.status() + 'Modal',
                        }, [
                            m('.progress-bar.progress-bar-success', {
                                connected: {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-success',
                                },
                                connecting: {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-warning progress-bar-striped active',
                                },
                                saving: {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-info progress-bar-striped active',
                                }
                            }[self.shareJSObservables.status()] || {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-danger',
                                }, [
                                    m('span.progress-bar-content', [
                                        {
                                            connected: 'Live editing mode ',
                                            connecting: 'Attempting to connect ',
                                            unsupported: 'Unsupported browser ',
                                            saving: 'Saving... '
                                        }[self.shareJSObservables.status()] || 'Unavailable: Live editing ',
                                        m('i.fa.fa-question-circle.fa-large')
                                    ])
                                ])
                            ])
                        ])
                    ]),
                    m('.col-md-3', [
                        m('.pull-right.btn-group.btn-group-sm', [
                            m('button#fileEditorRevert.btn.btn-warning', {onclick: function(){$(document).trigger('fileviewpage:revert');}}, 'Revert'),
                            m('button#fileEditorSave.btn.btn-success', {onclick: function() {$(document).trigger('fileviewpage:save');}}, 'Save')
                        ])
                    ])
                ]);
        };


        //crappy hack to delay creation of the editor
        //until we know this is the current file revsion
        self.enableEditing = function() {
            //Sometimes we can get here twice, check just in case
            if (self.editor || !self.context.currentUser.canEdit) return;
            var fileType = mime.lookup(self.file.name.toLowerCase());
            //Only allow files < 1MB to be editable
            if (self.file.size < 1048576 && fileType) { //May return false
                editor = EDITORS[fileType.split('/')[0]];
                if (editor) {
                    self.editor = Panel('Edit', editHeader, editor, [self.file.urls.content, self.file.urls.sharejs, self.editorMeta, self.shareJSObservables], false);
                    self.panels.splice(1, 0, self.editor);
                }
            }
        };

        self.panels = [
            Panel('Revisions', revisionsHeader, FileRevisionsTable, [self.file, self.node, self.enableEditing], true),
            // View has been removed to prefer the iframe method described below
            // Panel('View', null, FileRenderer, [self.file.urls.render, self.file.error], true),
        ];

    },
    view: function(ctrl) {
        return m('.file-view-page', [
            m.component(PanelToggler, m('h3', ctrl.file.name), ctrl.panels)
        ]);
    }
};

module.exports = function(context) {
    //Treebeard forces all mithril to load twice
    //To avoid destroying the page iframe this out side of mithril
    if (!context.file.urls.render) {
        $('#mfrIframe').html(context.file.error);
    } else {
        //Need token in url as we cannot send headers with an Iframe
        var mfrIframe = new pym.Parent('mfrIframe', context.file.urls.render + '&token=' + context.accessToken, {});
        $(document).on('fileviewpage:reload', function() {
            mfrIframe.sendMessage('reload');
        });
    }
    return m.component(FileViewPage, context);
};
