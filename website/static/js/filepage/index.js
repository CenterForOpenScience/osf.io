var $ = require('jquery');
var m = require('mithril');
var mime = require('js/mime');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

// Local requires
var utils = require('./util.js');
var FileEditor = require('./editor.js');
var makeClient = require('js/clipboard');
var FileRevisionsTable = require('./revisions.js');
var storageAddons = require('json-loader!storageAddons.json');
var CommentModel = require('js/comment');

var History = require('exports-loader?History!history');
var SocialShare = require('js/components/socialshare');

// Sanity
var Panel = utils.Panel;


var EDITORS = {'text': FileEditor};

var clipboardConfig = function(element, isInitialized) {
    if (!isInitialized) {
        makeClient(element);
    }
};

var CopyButton = {
    view: function(ctrl, params) {
        return m('span.input-group-btn', m('button.btn.btn-default.btn-md[type="button"]' +
            '[data-clipboard-text="' + params.link + '"]',
            {config: clipboardConfig, style: {height: params.height}},
            m('.fa.fa-copy')));
    }
};

var formatUrl = function(urlParams, showParam) {
    return 'view_only' in urlParams ? '?show=' + showParam + '&view_only=' + urlParams.view_only : '?show=' + showParam;
};

var SharePopover =  {
    view: function(ctrl, params) {
        var copyButtonHeight = '34px';
        var popoverWidth = '450px';
        var renderLink = params.link;
        var fileLink = window.location.href;

        var mfrHost = renderLink.substring(0, renderLink.indexOf('render'));
        return m('button#sharebutton.disabled.btn.btn-sm.btn-default.file-share', {onclick: function popOverShow() {
                var pop = document.getElementById('popOver');
                //This is bad, should only happen for Firefox, thanks @chrisseto
                if (!pop){
                    return window.setTimeout(popOverShow, 100);
                }
                m.render(document.getElementById('popOver'), [
                    m('ul.nav.nav-tabs.nav-justified', [
                        m('li.active', m('a[href="#share"][data-toggle="tab"]', 'Share')),
                        m('li', m('a[href="#embed"][data-toggle="tab"]', 'Embed'))
                    ]), m('br'),
                    m('.tab-content', [
                        m('.tab-pane.active#share', [
                            m('.input-group', [
                                CopyButton.view(ctrl, {link: renderLink, height: copyButtonHeight}), //workaround to allow button to show up on first click
                                m('input.form-control[readonly][type="text"][value="'+ renderLink +'"]')
                            ]),
                            SocialShare.ShareButtons.view(ctrl, {title: window.contextVars.file.name, url: fileLink})
                        ]),
                        m('.tab-pane#embed', [
                            m('p', 'Dynamically render iframe with JavaScript'),
                            m('textarea.form-control[readonly][type="text"][value="' +
                                '<style>' +
                                '.embed-responsive{position:relative;height:100%;}' +
                                '.embed-responsive iframe{position:absolute;height:100%;}' +
                                '</style>' +
                                '<script>window.jQuery || document.write(\'<script src="//code.jquery.com/jquery-1.11.2.min.js">\\x3C/script>\') </script>' +
                                '<link href="' + mfrHost + 'static/css/mfr.css" media="all" rel="stylesheet">' +
                                '<div id="mfrIframe" class="mfr mfr-file"></div>' +
                                '<script src="' + mfrHost + 'static/js/mfr.js">' +
                                '</script> <script>' +
                                    'var mfrRender = new mfr.Render("mfrIframe", "' + renderLink + '");' +
                                '</script>' + '"]'
                            ), m('br'),
                            m('p', 'Direct iframe with fixed height and width'),
                            m('textarea.form-control[readonly][value="' +
                                '<iframe src="' + renderLink + '" width="100%" scrolling="yes" height="' + params.height + '" marginheight="0" frameborder="0" allowfullscreen webkitallowfullscreen>"]'
                            )
                        ])
                    ])
                ]);
            },
            config: function(element, isInitialized) {
                if(!isInitialized){
                    var button = $(element).popover();
                    button.on('show.bs.popover', function(e){
                        //max-width used to override, and width used to create space for the mithril object to be injected
                        button.data()['bs.popover'].$tip.css('text-align', 'center').css('max-width', popoverWidth).css('width', popoverWidth);
                    });
                }
            },
            'data-toggle': 'popover', 'data-placement': 'bottom',
            'data-content': '<div id="popOver"></div>', 'title': 'Share',
            'data-container': 'body', 'data-html': 'true'
        }, 'Share');
    }
};

var FileViewPage = {
    controller: function(context) {
        var self = this;
        self.context = context;
        self.file = self.context.file;
        self.node = self.context.node;
        self.editorMeta = self.context.editor;
        self.isLatestVersion = false;

        self.selectLatest = function() {
            self.isLatestVersion = true;
        };
        if (self.file.provider === 'osfstorage') {
            self.canEdit = function() {
                return ((!self.file.checkoutUser) || (self.file.checkoutUser === self.context.currentUser.id)) ? self.context.currentUser.canEdit : false;
            };
            if (self.file.isPreregCheckout){
                m.render(document.getElementById('alertBar'), m('.alert.alert-warning[role="alert"]', m('span', [
                    m('strong', 'File is checked out.'),
                    ' This file has been checked out by a COS Preregistration Challenge Reviewer and will become available when review is complete.',
                ])));
            } else if ((self.file.checkoutUser) && (self.file.checkoutUser !== self.context.currentUser.id)) {
                m.render(document.getElementById('alertBar'), m('.alert.alert-warning[role="alert"]', m('span', [
                    m('strong', 'File is checked out.'),
                    ' This file has been checked out by a ',
                    m('a[href="/' + self.file.checkoutUser + '"]', 'collaborator'),
                    '. It needs to be checked in before any changes can be made.'
                ])));
            }
        } else if (self.file.provider === 'bitbucket' || self.file.provider === 'gitlab' || self.file.provider === 'onedrive') {
            self.canEdit = function() { return false; };  // Bitbucket, OneDrive, and GitLab are read-only
        } else {
            self.canEdit = function() {
                return self.context.currentUser.canEdit;
            };
        }

        $.extend(self.file.urls, {
            delete: waterbutler.buildDeleteUrl(self.file.path, self.file.provider, self.node.id),
            metadata: waterbutler.buildMetadataUrl(self.file.path, self.file.provider, self.node.id),
            revisions: waterbutler.buildRevisionsUrl(self.file.path, self.file.provider, self.node.id),
            content: waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id, {direct: true, mode: 'render'})
        });

        if ($osf.urlParams().branch) {
            var fileWebViewUrl = waterbutler.buildMetadataUrl(self.file.path, self.file.provider, self.node.id, {branch : $osf.urlParams().branch});
            $.ajax({
                dataType: 'json',
                async: true,
                url: fileWebViewUrl,
                beforeSend: $osf.setXHRAuthorization
            }).done(function(response) {
                window.contextVars.file.urls.external = response.data.attributes.extra.webView;
            });

            if (self.file.provider === 'github') {
                self.file.urls.revisions = waterbutler.buildRevisionsUrl(
                    self.file.path, self.file.provider, self.node.id,
                    {sha: $osf.urlParams().branch}
                );
            }
            else if (self.file.provider === 'bitbucket' || self.file.provider === 'gitlab') {
                self.file.urls.revisions = waterbutler.buildRevisionsUrl(
                    self.file.path, self.file.provider, self.node.id,
                    {branch: $osf.urlParams().branch}
                );
            }
            self.file.urls.content = waterbutler.buildDownloadUrl(self.file.path, self.file.provider, self.node.id, {direct: true, mode: 'render', branch: $osf.urlParams().branch});
        }

        $(document).on('fileviewpage:delete', function() {
            var title = 'Delete file?';
            var message = '<p class="overflow">' +
                    'Are you sure you want to delete <strong>' +
                    self.file.safeName + '</strong>?' + '</p>';


            bootbox.confirm({
                title: title,
                message: message,
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
        $(document).on('fileviewpage:checkout', function() {
            bootbox.confirm({
                title: 'Confirm file check out?',
                message: 'This would mean ' +
                    'other contributors cannot edit, delete or upload new versions of this file ' +
                    'as long as it is checked out. You can check it back in at anytime.',
                callback: function(confirm) {
                    if (!confirm) {
                        return;
                    }
                    $.ajax({
                        method: 'put',
                        url: window.contextVars.apiV2Prefix + 'files' + self.file.path + '/',
                        beforeSend: $osf.setXHRAuthorization,
                        contentType: 'application/json',
                        dataType: 'json',
                        data: JSON.stringify({
                            data: {
                                id: self.file.path.replace('/', ''),
                                type: 'files',
                                attributes: {
                                    checkout: self.context.currentUser.id
                                }
                            }
                        })
                    }).done(function(resp) {
                        window.location.reload();
                    }).fail(function(resp) {
                        $osf.growl('Error', 'Unable to check out file');
                    });
                },
                buttons:{
                    confirm:{
                        label: 'Check out file',
                        className: 'btn-warning'
                    }
                }
            });
        });
        $(document).on('fileviewpage:checkin', function() {
            $.ajax({
                method: 'put',
                url: window.contextVars.apiV2Prefix + 'files' + self.file.path + '/',
                beforeSend: $osf.setXHRAuthorization,
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({
                    data: {
                        id: self.file.path.replace('/', ''),
                        type: 'files',
                        attributes: {
                            checkout: null
                        }
                    }
                })
            }).done(function(resp) {
                window.location.reload();
            }).fail(function(resp) {
                $osf.growl('Error', 'Unable to check in file');
            });
        });
        $(document).on('fileviewpage:force_checkin', function() {
            bootbox.confirm({
                title: 'Force check in file?',
                message: 'This will check in the file for all users, allowing it to be edited. Are you sure?',
                buttons: {
                    confirm:{
                        label: 'Force check in',
                        className: 'btn-danger'
                    }
                },
                callback: function(confirm) {
                    if (!confirm) {
                        return;
                    }
                    $.ajax({
                        method: 'put',
                        url: window.contextVars.apiV2Prefix + 'files' + self.file.path + '/',
                        beforeSend: $osf.setXHRAuthorization,
                        contentType: 'application/json',
                        dataType: 'json',
                        data: JSON.stringify({
                            data: {
                                id: self.file.path.replace('/', ''),
                                type: 'files',
                                attributes: {
                                    checkout: null
                                }
                            }
                        })
                    }).done(function(resp) {
                        window.location.reload();
                    }).fail(function(resp) {
                        $osf.growl('Error', 'Unable to force check in file. Make sure you have admin privileges.');
                    });
                }

            });
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
            // Only allow files < 200kb to be editable (should sync with MFR limit)
            // No files on figshare are editable.
            if (self.file.size < 204800 && fileType && self.file.provider !== 'figshare') { //May return false
                var editor = EDITORS[fileType.split('/')[0]];
                if (editor) {
                    self.editor = new Panel('Edit', self.editHeader, editor, [self.file.urls.content, self.file.urls.sharejs, self.editorMeta, self.shareJSObservables], false);
                }
            }
            m.redraw(true);
        };

        //Hack to polyfill the Panel interface
        //Ran into problems with mithrils caching messing up with multiple "Panels"
        self.revisions = m.component(FileRevisionsTable, self.file, self.node, self.enableEditing, self.canEdit, self.selectLatest);
        self.revisions.selected = false;
        self.revisions.title = 'Revisions';

        // inform the mfr of a change in display size performed via javascript,
        // otherwise the mfr iframe will not update unless the document windows is changed.
        self.triggerResize = $osf.throttle(function () {
            $(document).trigger('fileviewpage:resize');
        }, 1000);

        self.mfrIframeParent = $('#mfrIframeParent');
        function toggleRevisions(e){
            if(self.editor){
                self.editor.selected = false;
            }
            var viewable = self.mfrIframeParent.is(':visible');
            var url = '';
            if (viewable){
                self.mfrIframeParent.toggle();
                self.revisions.selected = true;
                url = formatUrl(self.urlParams, 'revision');
            } else {
                self.mfrIframeParent.toggle();
                self.revisions.selected = false;
                url = formatUrl(self.urlParams, 'view');
            }
            var state = {
                scrollTop: $(window).scrollTop(),
            };
            History.pushState(state, 'OSF | ' + window.contextVars.file.name, url);
        }

        function changeVersionHeader(){
            document.getElementById('versionLink').style.display = 'inline';
            m.render(document.getElementById('versionLink'), m('a', {onclick: toggleRevisions}, document.getElementById('versionLink').innerHTML));
        }

        self.urlParams = $osf.urlParams();
        // The parser found a query so lets check what we need to do
        if ('show' in self.urlParams){
            if(self.urlParams.show === 'revision'){
                self.mfrIframeParent.toggle();
                self.revisions.selected = true;
            } else if (self.urlParams.show === 'view' || self.urlParams.show === 'edit'){
               self.revisions.selected = false;
           }
        }

        if(self.file.provider === 'osfstorage'){
            changeVersionHeader();
        }

        self.enableEditing();
    },
    view: function(ctrl) {
        //This code was abstracted into a panel toggler at one point
        //it was removed and shoved here due to issues with mithrils caching and interacting
        //With other non-mithril components on the page
        //anchor checking hack that will select if true
        var state = {
            scrollTop: $(window).scrollTop(),
        };

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

        var editButton = function() {
            if (ctrl.editor) {
                return m('button.btn' + (ctrl.editor.selected ? '.btn-primary' : '.btn-default'), {
                    onclick: function (e) {
                        e.preventDefault();
                        // atleast one button must remain enabled.
                        if ((!ctrl.editor.selected || panelsShown > 1)) {
                            ctrl.editor.selected = !ctrl.editor.selected;
                            ctrl.revisions.selected = false;
                            var url = formatUrl(ctrl.urlParams, 'view');
                            state = {
                                scrollTop: $(window).scrollTop(),
                            };
                            History.pushState(state, 'OSF | ' + window.contextVars.file.name, url);
                        }
                    }
                }, ctrl.editor.title);
            }
        };

        var link = $('iframe').attr('src') ? $('iframe').attr('src').substring(0, $('iframe').attr('src').indexOf('download') + 8) +
                '%26mode=render' : 'Data not available';
        var height = $('iframe').attr('height') ? $('iframe').attr('height') : '0px';

        m.render(document.getElementById('toggleBar'), m('.btn-toolbar.m-t-md', [
            ctrl.context.currentUser.canEdit && (!ctrl.canEdit()) && (ctrl.context.currentUser.isAdmin) && (ctrl.file.provider !== 'bitbucket') && (ctrl.file.provider !== 'gitlab') && (ctrl.file.provider !== 'onedrive') && !ctrl.context.file.isPreregCheckout ? m('.btn-group.m-l-xs.m-t-xs', [
                ctrl.isLatestVersion ? m('.btn.btn-sm.btn-default', {onclick: $(document).trigger.bind($(document), 'fileviewpage:force_checkin')}, 'Force check in') : null
            ]) : '',
            ctrl.canEdit() && (!ctrl.file.checkoutUser) && (ctrl.file.provider === 'osfstorage') ? m('.btn-group.m-l-xs.m-t-xs', [
                ctrl.isLatestVersion ? m('.btn.btn-sm.btn-default', {onclick: $(document).trigger.bind($(document), 'fileviewpage:checkout')}, 'Check out') : null
            ]) : '',
            (ctrl.canEdit() && (ctrl.file.checkoutUser === ctrl.context.currentUser.id) ) ? m('.btn-group.m-l-xs.m-t-xs', [
                ctrl.isLatestVersion ? m('.btn.btn-sm.btn-warning', {onclick: $(document).trigger.bind($(document), 'fileviewpage:checkin')}, 'Check in') : null
            ]) : '',
            // Special case whether or not to show the delete button for published Dataverse files
            // Special case to not show delete if file is preprint primary file
            // Special case to not show delete for public figshare files
            // Special case to not show force check-in for read-only providers
            (
                ctrl.canEdit() &&
                (ctrl.node.preprintFileId !== ctrl.file.id) &&
                    !(ctrl.file.provider === 'figshare' && ctrl.file.extra.status === 'public') &&
                (ctrl.file.provider !== 'osfstorage' || !ctrl.file.checkoutUser) &&
                (document.URL.indexOf('version=latest-published') < 0)
            ) ? m('.btn-group.m-l-xs.m-t-xs', [
                ctrl.isLatestVersion ? m('button.btn.btn-sm.btn-default.file-delete', {onclick: $(document).trigger.bind($(document), 'fileviewpage:delete') }, 'Delete') : null
            ]) : '',
            m('.btn-group.m-t-xs', [
                ctrl.isLatestVersion ? m('a.btn.btn-sm.btn-primary.file-download', {href: 'download'}, 'Download') : null
            ]),
            window.contextVars.node.isPublic? m('.btn-group.m-t-xs', [
                m.component(SharePopover, {link: link, height: height})
            ]) : '',
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
                            History.pushState(state, 'OSF | ' + window.contextVars.file.name, formatUrl(ctrl.urlParams, 'view'));
                        } else if (ctrl.mfrIframeParent.is(':visible') && !ctrl.editor){
                            ctrl.mfrIframeParent.toggle();
                            ctrl.revisions.selected = true;
                            History.pushState(state, 'OSF | ' + window.contextVars.file.name, formatUrl(ctrl.urlParams, 'revision'));
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
                        History.pushState(state, 'OSF | ' + window.contextVars.file.name, formatUrl(ctrl.urlParams, 'revision'));
                    } else {
                        ctrl.mfrIframeParent.toggle();
                        if (ctrl.editor) {
                            ctrl.editor.selected = false;
                        }
                        ctrl.revisions.selected = false;
                        History.pushState(state, 'OSF | ' + window.contextVars.file.name, formatUrl(ctrl.urlParams, 'view'));
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


// Initialize file comment pane
var $comments = $('.comments');
if ($comments.length) {
    var options = {
        nodeId: window.contextVars.node.id,
        nodeApiUrl: window.contextVars.node.urls.api,
        isRegistration: window.contextVars.node.isRegistration,
        page: 'files',
        rootId: window.contextVars.file.guid,
        fileId: window.contextVars.file.id,
        canComment: window.contextVars.currentUser.canComment,
        hasChildren: window.contextVars.node.hasChildren,
        currentUser: window.contextVars.currentUser,
        pageTitle: window.contextVars.file.name,
        inputSelector: '.atwho-input'
    };
    CommentModel.init('#commentsLink', '.comment-pane', options);
}


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
