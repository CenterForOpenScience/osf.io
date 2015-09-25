var $ = require('jquery');
var m = require('mithril');
var mime = require('js/mime');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

// Local requires
var utils = require('./util.js');
var FileEditor = require('./editor.js');
var FileRevisionsTable = require('./revisions.js');
var storageAddons = require('json!storageAddons.json');

// Sanity
var Panel = utils.Panel;


var EDITORS = {'text': FileEditor};


var FileViewPage = {
    controller: function(context) {
        var self = this;
        self.context = context;
        self.file = self.context.file;
        self.node = self.context.node;
        self.editorMeta = self.context.editor;
        //Force canEdit into a bool
        self.canEdit = m.prop(!!self.context.currentUser.canEdit);
        self.fileName = m.prop(self.file.name);
        self.fileNameEdit = m.prop(false);

        $.extend(self.file.urls, {
            delete: waterbutler.buildDeleteUrl(self.file.path, self.file.provider, self.node.id),
            metadata: waterbutler.buildMetadataUrl(self.file.path, self.file.provider, self.node.id),
            revisions: waterbutler.buildRevisionsUrl(self.file.path, self.file.provider, self.node.id),
            content: waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id, {accept_url: false, mode: 'render'})
        });

        if ($osf.urlParams().branch) {
            self.file.urls.revisions = waterbutler.buildRevisionsUrl(self.file.path, self.file.provider, self.node.id, {sha: $osf.urlParams().branch});
            self.file.urls.content = waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id, {accept_url: false, mode: 'render', branch: $osf.urlParams().branch});
        }

        $(document).on('fileviewpage:delete', function() {
            bootbox.confirm({
                title: 'Delete file?',
                message: '<p class="overflow">' +
                        'Are you sure you want to delete <strong>' +
                        self.file.safeName + '</strong>?' +
                    '</p>',
                callback: function(confirm) {
                    if (!confirm) {
                        return;
                    }
                    $.ajax({
                        type: 'DELETE',
                        url: self.file.urls.delete,
                        beforeSend: $osf.setXHRAuthorization
                    }).done(function() {
                        window.location = self.node.urls.files;
                    }).fail(function() {
                        $osf.growl('Error', 'Could not delete file.');
                    });
                },
                buttons:{
                    confirm:{
                        label:'Delete',
                        className:'btn-danger'
                    }
                }
            });
        });

        $(document).on('fileviewpage:download', function() {
            //replace mode=render with action=download for download count incrementation
            window.location = self.file.urls.content.replace('mode=render', 'action=download');
            return false;
        });

        self.shareJSObservables = {
            activeUsers: m.prop([]),
            status: m.prop('connecting'),
            userId: self.context.currentUser.id
        };

        self.editHeader = function() {
            return m('.row', [
                m('.col-sm-12', m('span[style=display:block;]', [
                    m('h3.panel-title',[m('i.fa.fa-pencil-square-o'), '   Edit ']),
                    m('.pull-right', [
                        m('.progress.no-margin.pointer', {
                            'data-toggle': 'modal',
                            'data-target': '#' + self.shareJSObservables.status() + 'Modal'
                        }, [
                            m('.progress-bar.p-h-sm.progress-bar-success', {
                                connected: {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-success'
                                },
                                connecting: {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-warning progress-bar-striped active'
                                },
                                saving: {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-info progress-bar-striped active'
                                }
                            }[self.shareJSObservables.status()] || {
                                    style: 'width: 100%',
                                    class: 'progress-bar progress-bar-danger'
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
                    ]))
                ]);
        };


        // Hack to delay creation of the editor
        // until we know this is the current file revision
        self.enableEditing = function() {
            // Sometimes we can get here twice, check just in case
            if (self.editor || !self.canEdit()) {
                m.redraw(true);
                return;
            }
            var fileType = mime.lookup(self.file.name.toLowerCase());
            // Only allow files < 1MB to be editable
            if (self.file.size < 1048576 && fileType) { //May return false
                var editor = EDITORS[fileType.split('/')[0]];
                if (editor) {
                    self.editor = new Panel('Edit', self.editHeader, editor, [self.file.urls.content, self.file.urls.sharejs, self.editorMeta, self.shareJSObservables], false);
                }
            }
            m.redraw(true);
        };

        //Hack to polyfill the Panel interface
        //Ran into problems with mithrils caching messing up with multiple "Panels"
        self.revisions = m.component(FileRevisionsTable, self.file, self.node, self.enableEditing, self.canEdit);
        self.revisions.selected = false;
        self.revisions.title = 'Revisions';

        // inform the mfr of a change in display size performed via javascript,
        // otherwise the mfr iframe will not update unless the document windows is changed.
        self.triggerResize = $osf.throttle(function () {
            $(document).trigger('fileviewpage:resize');
        }, 1000);

        self.mfrIframeParent = $('#mfrIframeParent');

        //$(document).on('fileviewpage:rename', function() {
        //    $(document).trigger('fileviewpage:rename');
        //    console.log('Here');
        //    if(!self.canEdit) {
        //        return;
        //    }
        //
        //    var $fileName = $('#fileName');
        //    $.fn.editable.defaults.mode = 'inline';
        //    $fileName.editable({
        //        type: 'POST',
        //        beforeSend: $osf.setXHRAuthorization,
        //        url: waterbutler.moveUrl(),
        //        headers: {
        //            'Content-Type': 'Application/json'
        //        },
        //        data: JSON.stringify({
        //            'rename': rename,
        //            'conflict': conflict,
        //            'source': waterbutler.toJsonBlob(from),
        //            'destination': waterbutler.toJsonBlob(to),
        //        }),
        //        validate: function(value) {
        //            if($.trim(value) === ''){
        //                $osf.growl('Error', 'The  file name cannot be empty.', {timeout: 5000});
        //            } else if(value.length > 100){
        //                $osf.growl('Error', 'The file name cannot be more than 100 characters.', {timeout: 5000});
        //            }
        //        },
        //        success: function(response, value) {
        //            window.location.href = self.context.urls.base + encodeURIComponent(value) + '/';
        //        },
        //        error: function(response) {
        //            var msg = response.responseJSON.message_long;
        //            if (msg) {
        //                return msg;
        //            } else {
        //                // Log unexpected error with Raven
        //                Raven.captureMessage('Error in renaming file', {
        //                    url: waterbutler.moveUrl(),
        //                    responseText: response.responseText,
        //                    statusText: response.statusText
        //                });
        //                $osf.growl('Error', 'Error in renaming file.');
        //            }
        //        }
        //    });
        //});

        // Checks for good formatting and duplication
        self.validateRename = function(name, callback) {
            if($.trim(name) === ''){
                $osf.growl('Error', 'The  file name cannot be empty.', {timeout: 5000});
                return;
            } else if(name.length > 100){
                $osf.growl('Error', 'The file name cannot be more than 100 characters.', {timeout: 5000});
                return;
            }
            var parent = self.file.parent();
            for(var i = 0; i < parent.children.length; i++) {
                var child = parent.children[i];
                if (child.data.name === name && child.id !== self.file.id) {
                    self.modal.update(m('', [
                        m('p', 'An item named "' + name + '" already exists in this location.')
                    ]), m('', [
                        m('span.btn.btn-info', {onclick: callback.bind(self, 'keep')}, 'Keep both'),
                        m('span.btn.btn-default', {onclick: function() {self.modal.dismiss();}}, 'Cancel'),
                        m('span.btn.btn-primary', {onclick: callback.bind(self, 'replace')}, 'Replace'),
                    ]), m('h3.break-word.modal-title', 'Replace "' + name + '"?'));
                    return;
                }
            }
            callback('replace');
        };

        self.renameFile = function(to, from, rename, conflict) {
            self.modal.dismiss();
            if (to.id === from.parentID && (!rename || rename == from.data.name)) {
                return;
            }
            from.data.status = 'rename';
            from.move(to.id);

            $.ajax({
                type: 'POST',
                beforeSend: $osf.setXHRAuthorization,
                url: waterbutler.moveUrl(),
                headers: {
                    'Content-Type': 'Application/json'
                },
                data: JSON.stringify({
                    'rename': rename,
                    'conflict': conflict,
                    'source': waterbutler.toJsonBlob(from),
                    'destination': waterbutler.toJsonBlob(to),
                })
            }).done(function(response, _, xhr) {
                $osf.growl('Success', 'Renamed to ' + rename + '.', 'success');
            })
        };

        if(self.canEdit) {
            $(document).trigger('fileviewpage:rename');
            var $fileName = $('#fileName');
            $.fn.editable.defaults.mode = 'inline';
            $fileName.editable({
                type: 'POST',
                beforeSend: $osf.setXHRAuthorization,
                url: waterbutler.moveUrl(),
                headers: {
                    'Content-Type': 'Application/json'
                },
                data: JSON.stringify({
                    'rename': rename,
                    'conflict': conflict,
                    'source': waterbutler.toJsonBlob(from),
                    'destination': waterbutler.toJsonBlob(to),
                }),
                validate: function(value) {
                    if($.trim(value) === ''){
                        $osf.growl('Error', 'The  file name cannot be empty.', {timeout: 5000});
                    } else if(value.length > 100){
                        $osf.growl('Error', 'The file name cannot be more than 100 characters.', {timeout: 5000});
                    }
                },
                success: function(response, value) {
                    window.location.href = self.context.urls.base + encodeURIComponent(value) + '/';
                },
                error: function(response) {
                    var msg = response.responseJSON.message_long;
                    if (msg) {
                        return msg;
                    } else {
                        // Log unexpected error with Raven
                        Raven.captureMessage('Error in renaming file', {
                            url: waterbutler.moveUrl(),
                            responseText: response.responseText,
                            statusText: response.statusText
                        });
                        $osf.growl('Error', 'Error in renaming file.');
                    }
                }
            });
        }
    },
    view: function(ctrl) {
        //This code was abstracted into a panel toggler at one point
        //it was removed and shoved here due to issues with mithrils caching and interacting
        //With other non-mithril components on the page
        var panelsShown = (
            ((ctrl.editor && ctrl.editor.selected) ? 1 : 0) + // Editor panel is active
            (ctrl.mfrIframeParent.is(':visible') ? 1 : 0)    // View panel is active
        );
        var mfrIframeParentLayout;
        var fileViewPanelsLayout;

        if (panelsShown === 2) {
            // view | edit
            mfrIframeParentLayout = 'col-sm-6';
            fileViewPanelsLayout = 'col-sm-6';
        } else {
            // view
            if (ctrl.mfrIframeParent.is(':visible')) {
                mfrIframeParentLayout = 'col-sm-12';
                fileViewPanelsLayout = '';
            } else {
                // edit or revisions
                mfrIframeParentLayout = '';
                fileViewPanelsLayout = 'col-sm-12';
            }
        }
        $('#mfrIframeParent').removeClass().addClass(mfrIframeParentLayout);
        $('.file-view-panels').removeClass().addClass('file-view-panels').addClass(fileViewPanelsLayout);

        if(ctrl.file.urls.external && !ctrl.file.privateRepo) {
            m.render(document.getElementById('externalView'), [
                m('p.text-muted', 'View this file on ', [
                    m('a', {href:ctrl.file.urls.external}, storageAddons[ctrl.file.provider].fullName)
                ], '.')
            ]);
        }

        // Renders the name of the file.
        //m.render(document.getElementById('fileNameDiv'), m((ctrl.fileNameEdit()) ? '' : 'h2.break-word',
        //    {onclick: ctrl.editTitle, contenteditable: ctrl.fileNameEdit()}, ctrl.fileName()));

        var editButton = function() {
            if (ctrl.editor) {
                return m('button.btn' + (ctrl.editor.selected ? '.btn-primary' : '.btn-default'), {
                    onclick: function (e) {
                        e.preventDefault();
                        // atleast one button must remain enabled.
                        if ((!ctrl.editor.selected || panelsShown > 1)) {
                            ctrl.editor.selected = !ctrl.editor.selected;
                            ctrl.revisions.selected = false;
                        }
                    }
                }, ctrl.editor.title);
            }
        };
        m.render(document.getElementById('toggleBar'), m('.btn-toolbar.m-t-md', [
            // Special case whether or not to show the delete button for published Dataverse files
            (ctrl.canEdit() && $(document).context.URL.indexOf('version=latest-published') < 0 ) ? m('.btn-group.m-l-xs.m-t-xs', [
                m('button.btn.btn-sm.btn-danger.file-delete', {onclick: $(document).trigger.bind($(document), 'fileviewpage:delete')}, 'Delete')
            ]) : '',
            m('.btn-group.m-t-xs', [
                m('button.btn.btn-sm.btn-primary.file-download', {onclick: $(document).trigger.bind($(document), 'fileviewpage:download')}, 'Download')
            ]),
            m('.btn-group.btn-group-sm.m-t-xs', [
               ctrl.editor ? m( '.btn.btn-default.disabled', 'Toggle view: ') : null
            ].concat(
                m('button.btn' + (ctrl.mfrIframeParent.is(':visible') ? '.btn-primary' : '.btn-default'), {
                    onclick: function (e) {
                        e.preventDefault();
                        // at least one button must remain enabled.
                        if (!ctrl.mfrIframeParent.is(':visible') || panelsShown > 1) {
                            ctrl.mfrIframeParent.toggle();
                            ctrl.revisions.selected = false;
                        } else if (ctrl.mfrIframeParent.is(':visible') && !ctrl.editor){
                            ctrl.mfrIframeParent.toggle();
                            ctrl.revisions.selected = true;
                        }
                    }
                }, 'View'), editButton())
            ),
            m('.btn-group.m-t-xs', [
                m('button.btn.btn-sm' + (ctrl.revisions.selected ? '.btn-primary': '.btn-default'), {onclick: function(){
                    var editable = ctrl.editor && ctrl.editor.selected;
                    var viewable = ctrl.mfrIframeParent.is(':visible');
                    if (editable || viewable){
                        if (viewable){
                            ctrl.mfrIframeParent.toggle();
                        }
                        if (editable) {
                            ctrl.editor.selected = false;
                        }
                        ctrl.revisions.selected = true;
                    } else {
                        ctrl.mfrIframeParent.toggle();
                        if (ctrl.editor) {
                            ctrl.editor.selected = false;
                        }
                        ctrl.revisions.selected = false;
                    }
                }}, 'Revisions')
            ])
        ]));

        if (ctrl.revisions.selected){
            return m('.file-view-page', m('.panel-toggler', [
                m('.row', ctrl.revisions)
            ]));
        }
        var editDisplay = (ctrl.editor && !ctrl.editor.selected) ? 'display:none' : '' ;
        ctrl.triggerResize();
        return m('.file-view-page', m('.panel-toggler', [
            m('.row[style="' + editDisplay + '"]', m('.col-sm-12', ctrl.editor),
             m('.row[style="display:none"]', ctrl.revisions))
        ]));
    }
};

module.exports = function(context) {
    // Treebeard forces all mithril to load twice, to avoid
    // destroying the page iframe this out side of mithril.
    if (!context.file.urls.render) {
        $('#mfrIframe').html(context.file.error);
    } else {
        var url = context.file.urls.render;
        if (navigator.appVersion.indexOf('MSIE 9.') !== -1) {
            url += url.indexOf('?') > -1 ? '&' : '?';
            url += 'cookie=' + (document.cookie.match(window.contextVars.cookieName + '=(.+?);|$')[1] || '');
        }

        if (window.mfr !== undefined) {
            var mfrRender = new mfr.Render('mfrIframe', url, {}, 'cos_logo.png');
            $(document).on('fileviewpage:reload', function() {
                mfrRender.reload();
            });
            $(document).on('fileviewpage:resize', function() {
                mfrRender.resize();
            });
        }

    }

    return m.component(FileViewPage, context);
};
