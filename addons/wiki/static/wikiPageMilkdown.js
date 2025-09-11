'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var diffTool = require('js/diffTool');
var _ = require('js/rdmGettext')._;
var yjs = require('yjs');
var yWebsocket = require('y-websocket');
var yIndexeddb = require('y-indexeddb');
var yProseMirror = require('y-prosemirror');
import * as mCore from '@milkdown/core';
import * as mCommonmark from '@milkdown/preset-commonmark';
import * as mNord from '@milkdown/theme-nord';
import * as mEmoji from '@milkdown/plugin-emoji';
import * as mUpload from '@milkdown/plugin-upload';
import * as mMath from '@milkdown/plugin-math';
import * as mClipboard from '@milkdown/plugin-clipboard';
import * as mGfm from '@milkdown/preset-gfm';
import * as mBlock from '@milkdown/plugin-block';
import * as mListener from '@milkdown/plugin-listener';
import * as mPrism from '@milkdown/plugin-prism';
import * as mIndent from '@milkdown/plugin-indent';
import * as mUtils from '@milkdown/utils';
import * as mCollab from '@milkdown/plugin-collab';
import * as mCursor from '@milkdown/plugin-cursor';
require('@milkdown/theme-nord/style.css');
require('@milkdown/prose/view/style/prosemirror.css');
require('@milkdown/prose/tables/style/tables.css');
require('katex/dist/katex.min.css');

var THROTTLE = 500;
var headNum = 1;
var mEdit;
var mView;
var readonly = true;
const editable = () => !readonly;
var promises = [];
var imageFolder = 'Wiki images';
var validImgExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp'];
const doc = new yjs.Doc();
const docId = window.contextVars.wiki.metadata.docId;
const wikiCtx = window.contextVars;
const wikiId = (wikiCtx.wiki.wikiName === 'home') ? wikiCtx.node.id : window.contextVars.wiki.wikiID;
const wsPrefix = (window.location.protocol === 'https:') ? 'wss://' : 'ws://';
const wsUrl = wsPrefix + window.contextVars.wiki.urls.y_websocket;

import { underlineSchema, underlineInputRule, remarkUnderlineToMarkdown, remarkUnderlineFromMarkdown, toggleUnderlineCommand } from './underline.js';
import { colortextSchema, colortextInputRule, remarkColortextToMarkdown, remarkColortextFromMarkdown, toggleColortextCommand } from './colortext.js';
import { extendedImageSchemaPlugin, extendedInsertImageCommand, extendedUpdateImageCommand, updatedInsertImageInputRule } from './image.js';
import { linkInputRuleCosutom } from './link.js';
import { customHeadingIdGenerator } from './heading.js';

async function createMView(editor, markdown) {
    if (editor && editor.destroy) {
        editor.destroy();
    }
    var viewonly = true;
    const editable = () => !viewonly;
    mView = await mCore.Editor
        .make()
        .config(ctx => {
            ctx.set(mCore.rootCtx, '#mView');
            ctx.set(mCore.defaultValueCtx, markdown);
            ctx.update(mCommonmark.headingIdGenerator.key, () => customHeadingIdGenerator);
            ctx.update(mCore.editorViewOptionsCtx, (prev) => ({
                ...prev,
                editable,
            }));
        })
        .config(mNord.nord)
        .use(mCommonmark.commonmark)
        .use([remarkUnderlineToMarkdown, remarkUnderlineFromMarkdown, underlineSchema, underlineInputRule, toggleUnderlineCommand])
        .use([remarkColortextToMarkdown, remarkColortextFromMarkdown, colortextSchema, colortextInputRule, toggleColortextCommand])
        .use([linkInputRuleCosutom, updatedInsertImageInputRule])
        .use(mEmoji.emoji)
        .use(mUpload.upload)
        .use(mMath.math)
        .use(mClipboard.clipboard)
        .use(mGfm.gfm)
        .use(mBlock.block)
        .use(mListener.listener)
        .use(mPrism.prism)
        .use(mIndent.indent)
        .use(mCollab.collab)
        .use([extendedImageSchemaPlugin])
        .create();
}

async function createMEditor(editor, vm, template) {
    if (editor && editor.destroy) {
        editor.destroy();
    }
    const enableHtmlFileUploader = false;
    const uploader = async (files, schema) => {
        // You can handle whatever the file can be upload to GRDM.
        var renderInfo = await localFileHandler(files);
        const attachments = [];
        for (let i = 0; i < files.length; i++) {
          var file = files.item(i);
          if (!file) {
            continue;
          }
          attachments.push(file);
        }
        const data = [];
        for(let i = 0; i < renderInfo.length; i++){
            data.push({alt: renderInfo[i]['name'], src: renderInfo[i]['url']});
        }
        const ret = data.map(({ alt, src }) => {
            var ext = getExtension(alt);
            if(!(validImgExtensions.includes(ext))){
                var attrs={ title: alt, href: src };
                    return schema.nodes.paragraph.createAndFill({}, schema.text(attrs.title, [schema.marks.link.create(attrs)]));
            }else{
                return schema.nodes.image.createAndFill({ src, alt });
            }
        });
        return ret;
    };

    const indexeddbProvider = wikiId ? new yIndexeddb.IndexeddbPersistence(wikiId, doc) : (console.error('Invalid wikiId: it must not be null, undefined, or empty'), null);
    const wsProvider = new yWebsocket.WebsocketProvider(wsUrl, docId, doc);

    mEdit = await mCore.Editor
        .make()
        .config(ctx => {
            ctx.set(mCore.rootCtx, '#mEditor');
            ctx.update(mCommonmark.headingIdGenerator.key, () => customHeadingIdGenerator);
            ctx.update(mUpload.uploadConfig.key, (prev) => ({
                ...prev,
                uploader,
                enableHtmlFileUploader,
            }));
            const debouncedMarkdownUpdated = $osf.debounce(async (ctx, markdown, prevMarkdown) => {
                const compareWidgetElement = document.getElementById("compareWidget");

                if (compareWidgetElement && compareWidgetElement.style.display !== 'none') {
                    vm.viewVM.displaySource(markdown);
                }

                const view = ctx.get(mCore.editorViewCtx);
                const state = view.state;
                const undoElement = document.getElementById("undoWiki");
                // set undo able
                if(state["y-undo$"] !== undefined && (state["y-undo$"].undoManager.undoStack).length !== 0){
                    undoElement.disabled = false;
                    document.getElementById("msoUndo").style.opacity = 1;
                }
            }, 300);
            ctx.get(mListener.listenerCtx).markdownUpdated((ctx, markdown, prevMarkdown) => {
                debouncedMarkdownUpdated(ctx, markdown, prevMarkdown);
            });
            ctx.update(mCore.editorViewOptionsCtx, (prev) => ({
                ...prev,
                editable,
            }));
        })
        .config(mNord.nord)
        .use(mCommonmark.commonmark)
        .use([extendedInsertImageCommand, extendedUpdateImageCommand])
        .use([remarkUnderlineToMarkdown, remarkUnderlineFromMarkdown, underlineSchema, underlineInputRule, toggleUnderlineCommand])
        .use([remarkColortextToMarkdown, remarkColortextFromMarkdown, colortextSchema, colortextInputRule, toggleColortextCommand])
        .use([linkInputRuleCosutom, updatedInsertImageInputRule])
        .use(mEmoji.emoji)
        .use(mUpload.upload)
        .use(mMath.math)
        .use(mClipboard.clipboard)
        .use(mGfm.gfm)
        .use(mBlock.block)
        .use(mListener.listener)
        .use(mPrism.prism)
        .use(mIndent.indent)
        .use(mCollab.collab)
        .use(mCursor.cursor)
        .use([extendedImageSchemaPlugin])
        .create();

    mEdit.action((ctx) => {
        const collabService = ctx.get(mCollab.collabServiceCtx);
        wsProvider.on('status', event => {
            vm.status(event.status);
            if (vm.status() !== 'connecting') {
                vm.updateStatus();
            }
            vm.throttledUpdateStatus();
        });
        wsProvider.on('connection-error', WSClosedEvent => {
            vm.status('disconnected');
            vm.updateStatus();
            vm.throttledUpdateStatus();
        });
        const fullname = window.contextVars.currentUser.fullname;
        wsProvider.awareness.setLocalStateField('user', { name: fullname, color: '#ffb61e'});
        collabService.bindDoc(doc).setAwareness(wsProvider.awareness);
        wsProvider.once('synced', async (isSynced) => {
            if (isSynced) {
                collabService
                .applyTemplate(template, (remoteNode, templateNode) => {
                    // if no remote node content, apply current to displaySource
                    if (remoteNode.textContent.length === 0) {
                        vm.viewVM.displaySource(template);
                        return true;
                    } else {
                        const view = ctx.get(mCore.editorViewCtx);
                        const serializer = ctx.get(mCore.serializerCtx);
                        const toMarkdown = serializer(remoteNode);
                        vm.viewVM.displaySource(toMarkdown);
                        return false;
                    }
                })
                .connect();
            }
        });
    });

}

function ViewWidget(visible, version, viewText, rendered, contentURL, allowMathjaxification, allowFullRender, editor) {
    var self = this;
    self.version = version;
    self.viewText = viewText; // comes from EditWidget.viewText
    self.rendered = rendered;
    self.visible = visible;
    self.allowMathjaxification = allowMathjaxification;
    self.editor = editor;
    self.allowFullRender = allowFullRender;
    self.renderTimeout = null;
    self.displaySource = ko.observable('');
    self.debouncedAllowFullRender = $osf.debounce(function() {
        self.allowFullRender(true);
    }, THROTTLE);

    self.renderMarkdown = function(rawContent){
       createMView(mView, rawContent);
    };

    self.displayText =  ko.computed(function() {
        self.allowFullRender();
        var requestURL;
        if (typeof self.version() !== 'undefined') {
            if (self.version() === 'preview') {
                var toMarkdown = '';
                if (mEdit !== undefined) {
                    mEdit.action((ctx) => {
                        const view = ctx.get(mCore.editorViewCtx);
                        const serializer = ctx.get(mCore.serializerCtx);
                        toMarkdown = serializer(view.state.doc);
                    });
                }
                self.displaySource(toMarkdown);
                if (document.getElementById("editWysiwyg").style.display === "none"){
                    document.getElementById("mMenuBar").style.display = "";
                    document.getElementById("mEditorFooter").style.display = "";
                }
                document.getElementById("mEditor").style.display = "";
                document.getElementById("wikiViewRender").style.display = "none";
            } else {
                document.getElementById("mMenuBar").style.display = "none";
                document.getElementById("mEditor").style.display = "none";
                const milkdownDivs = document.getElementById("mEditor").querySelectorAll('div.milkdown');
                if (milkdownDivs.length > 0) {
                    milkdownDivs[0].remove();
                }
                document.getElementById("mEditorFooter").style.display = "none";
                document.getElementById("wikiViewRender").style.display = "";
                if (self.version() === 'current') {
                    requestURL = contentURL;
                } else {
                    requestURL= contentURL + self.version();
                }
                var request = $.ajax({
                    url: requestURL
                });

                request.done(function (resp) {
                    if(self.visible()) {
                        if (resp.wiki_content){
                            var rawContent = resp.wiki_content;
                        } else if(window.contextVars.currentUser.canEdit) {
                            var rawContent = _('*Add important information, links, or images here to describe your project.*');
                        } else {
                            var rawContent = _('*No wiki content.*');
                        }
                        // Render raw markdown
                        self.rendered(self.renderMarkdown(rawContent));
                        self.displaySource(rawContent);
                    }
                });
            }
        } else {
            self.displaySource('');
        }
    });
}

// currentText comes from ViewWidget.displayText
function CompareWidget(visible, compareVersion, currentText, rendered, contentURL) {
    var self = this;
    self.compareVersion = compareVersion;
    self.currentText = currentText;
    self.rendered = rendered;
    self.visible = visible;
    self.contentURL = contentURL;
    self.compareSource = ko.observable('');

    self.compareText = ko.computed(function() {
        var requestURL;
        if (self.compareVersion() === 'current') {
            requestURL = self.contentURL;
        } else {
            requestURL= self.contentURL + self.compareVersion();
        }
        var request = $.ajax({
            url: requestURL
        });
        request.done(function (resp) {
            var rawText = resp.wiki_content;
            self.compareSource(rawText);
        });

    });

    self.compareOutput = ko.computed(function() {
        var output = diffTool.diff(self.compareSource(), self.currentText());
        self.rendered(output);
        return output;
    }).extend({ notify: 'always' });

}

var defaultOptions = {
    viewVisible: true,
    compareVisible: false,
    menuVisible: true,
    canEdit: true,
    viewVersion: 'current',
    compareVersion: 'previous',
    urls: {
        content: '',
        draft: '',
        page: ''
    },
    metadata: {}
};

function ViewModel(options){
    var self = this;
    // enabled?
    self.viewVis = ko.observable(options.viewVisible);
    self.compareVis = ko.observable(options.compareVisible);
    self.menuVis = ko.observable(options.menuVisible);
    // singleVis : checks if the item visible is the only visible column
    self.singleVis = ko.pureComputed(function(){
        var visible = 0;
        var single;
        if(self.viewVis()){
            visible++;
            single = 'view';
        }
        if(self.compareVis()){
            visible++;
            single = 'compare';
        }
        if(visible === 1){
            return single;
        }
        return false;
    });

    self.pageTitle = $(document).find('title').text();

    self.status = ko.observable('connecting');
    self.throttledStatus = ko.observable(self.status());

    self.compareVersion = ko.observable(options.compareVersion);
    self.viewVersion = ko.observable(options.viewVersion);
    self.draftURL = options.urls.draft;
    self.contentURL = options.urls.content;
    self.pageURL = options.urls.page;
    self.editorMetadata = options.metadata;
    self.canEdit = options.canEdit;

    self.viewText = ko.observable('');
    self.renderedView = ko.observable('');
    self.renderedCompare = ko.observable('');
    self.allowMathjaxification = ko.observable(true);
    self.allowFullRender = ko.observable(true);
    self.viewVersionDisplay = ko.computed(function() {
        var versionString = '';
        if (self.viewVersion() === 'preview') {
            versionString = _('Live preview');
        } else if (self.viewVersion() === 'current'){
            versionString = _('Current version');
        } else if (self.viewVersion() === 'previous'){
            versionString = _('Previous version');
        } else {
            versionString = _('Version ') + self.viewVersion();
        }
        return versionString;
    });

    self.collaborativeStatus = ko.computed(function() {
        if (self.viewVersion() === 'preview') {
            document.getElementById("collaborativeStatus").style.display = "";
        } else {
            document.getElementById("collaborativeStatus").style.display = "none";
        }
    });
    // Save initial query params (except for the "mode" query params, which are handled
    // by self.currentURL), so that we can preserve them when we mutate window.history.state
    var initialParams = $osf.urlParams();
    delete initialParams.view;
    delete initialParams.edit;
    delete initialParams.compare;
    delete initialParams.menu;
    self.initialQueryParams = $.param(initialParams);

    self.modalTarget = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connected':
                return '#connectedModal';
            case 'connecting':
                return '#connectingModal';
            case 'unsupported':
                return '#unsupportedModal';
            default:
                return '#disconnectedModal';
        }
    });

    self.statusDisplay = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connected':
                return 'Live editing mode';
            case 'connecting':
                return 'Attempting to connect';
            default:
                return 'Unavailable: Live editing';
        }
    });

    // Throttle the display when updating status.
    self.updateStatus = function() {
        self.throttledStatus(self.status());
    };

    self.throttledUpdateStatus = $osf.throttle(self.updateStatus, 4000, {leading: false});

    self.progressBar = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connected':
                return {
                    class: 'progress-bar progress-bar-success',
                    style: 'width: 100%'
                };
            case 'connecting':
                return {
                    class: 'progress-bar progress-bar-warning progress-bar-striped active',
                    style: 'width: 100%'
                };
            default:
                return {
                    class: 'progress-bar progress-bar-danger',
                    style: 'width: 100%'
                };
        }
    });

    self.currentURL = ko.computed(function() {
        // Do not change URL for incompatible browsers
        if (typeof window.history.replaceState === 'undefined') {
            return;
        }

        var paramPrefix = '?';
        var url = self.pageURL;
        // Preserve initial query params
        if (self.initialQueryParams) {
            url += paramPrefix + self.initialQueryParams;
            paramPrefix = '&';
        }
        // Default view is special cased
        if (self.viewVis() && self.viewVersion() === 'current' && !self.compareVis() && self.menuVis()) {
            window.history.replaceState({}, '', url);
            return;
        }

        if (self.viewVis()) {
            url += paramPrefix + 'view';
            paramPrefix = '&';
            if  ((self.viewVersion() !== 'current' )) {
                url += '=' + self.viewVersion();
            }
        }
        if (self.compareVis()) {
            url += paramPrefix + 'compare';
            paramPrefix = '&';
            if (self.compareVersion() !== 'previous'){
                url += '=' + self.compareVersion();
            }
        }
        if (self.menuVis()) {
            url += paramPrefix + 'menu';
        }

        window.history.replaceState({}, self.pageTitle, url);
    });

    var request = $.ajax({
        url: self.contentURL
    });
    request.done(function (resp) {
        self.rawContent = resp.wiki_content;
    });

    self.viewVM = new ViewWidget(self.viewVis, self.viewVersion, self.viewText, self.renderedView, self.contentURL, self.allowMathjaxification, self.allowFullRender, self.editor);
    self.compareVM = new CompareWidget(self.compareVis, self.compareVersion, self.viewVM.displaySource, self.renderedCompare, self.contentURL);

    if(self.canEdit) {
        var request = $.ajax({
            url: self.contentURL
        });
        var rawContent = '';
        request.done(function (resp) {
            if (resp.wiki_content){
                rawContent = resp.wiki_content;
            }
            if ((self.viewVersion() === 'preview' )) {
                mEdit = createMEditor(mEdit, self, rawContent);
            }
        });
    }
    var bodyElement = $('body');
    bodyElement.on('togglePanel', function (event, panel, display) {
        // Update self.viewVis, or self.compareVis in viewmodel
        self[panel + 'Vis'](display);
        //URL needs to be a computed observable, and this should just update the panel states, which will feed URL
        // Switch view to correct version
        if (panel === 'view') {
            if(!display && self.compareVis()){
                self.viewVersion('preview');
            }
        }

        if (panel === 'compare') {
            if(display && self.compareVis()){
                self.viewVersion('preview');
                var toMarkdown = '';
                mEdit.action((ctx) => {
                    const view = ctx.get(mCore.editorViewCtx);
                    const serializer = ctx.get(mCore.serializerCtx);
                    toMarkdown = serializer(view.state.doc);
                });
                self.viewVM.displaySource(toMarkdown);
            }
        }

    });

    bodyElement.on('toggleMenu', function(event, menuVisible) {
        self.menuVis(menuVisible);
    });

    self.undoWiki = function() {
        mEdit.action((ctx) => {
            var view = ctx.get(mCore.editorViewCtx);
            var state = view.state;
            view.focus();
            yProseMirror.undo(state);
            if((state["y-undo$"].undoManager.undoStack).length === 0){
                document.getElementById("undoWiki").disabled = true;
                document.getElementById("msoUndo").style.opacity = 0.3;
            }
            document.getElementById("redoWiki").disabled = false;
            document.getElementById("msoRedo").style.opacity = 1;
        });
    };
    self.redoWiki = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const state = view.state;
            view.focus();
            yProseMirror.redo(state);
            if((state["y-undo$"].undoManager.redoStack).length === 0){
                document.getElementById("redoWiki").disabled = true;
                document.getElementById("msoRedo").style.opacity = 0.3;
            }
            document.getElementById("undoWiki").disabled = false;
            document.getElementById("msoUndo").style.opacity = 1;
        });
    };
    self.strong = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            mUtils.callCommand(mCommonmark.toggleStrongCommand.key)(ctx);
        });
    };
    self.getLinkInfo = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const state = view.state;
            const { from, to } = state.selection;
            const markType = ctx.get(mCore.schemaCtx).marks.link;

            var linkHref = document.getElementById("linkSrc");
            var linkTitle = document.getElementById("linkTitle");

            linkHref.value = '';
            linkTitle.value = '';

            state.doc.nodesBetween(from, to, (node, pos) => {
                const linkMark = node.marks.find(mark => mark.type === markType);
                if (linkMark) {
                    const href = linkMark.attrs.href || '';
                    const title = linkMark.attrs.title || '';

                    linkHref.value = href;
                    linkTitle.value = title;
                }
            });
        });
    };
    self.link = function() {
        var linkHref = document.getElementById("linkSrc");
        var linkTitle = document.getElementById("linkTitle");
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const state = view.state;
            const { from, to } = state.selection;
            const markType = ctx.get(mCore.schemaCtx).marks.link;

            let hasLink = false;
            state.doc.nodesBetween(from, to, node => {
                if (node.marks.some(mark => mark.type === markType)) {
                    hasLink = true;
                }
            });

            if (hasLink && linkHref.value === '') {
                mUtils.callCommand(mCommonmark.toggleLinkCommand.key, {})(ctx);
            } else if (hasLink && linkHref.value !== '') {
                mUtils.callCommand(mCommonmark.updateLinkCommand.key, {
                    href: linkHref.value,
                    title: linkTitle.value
                })(ctx);
            } else {
                mUtils.callCommand(mCommonmark.toggleLinkCommand.key, {
                    href: linkHref.value,
                    title: linkTitle.value
                })(ctx);
            }
            $('.modal').modal('hide');
            linkHref.value = '';
            linkTitle.value = '';
            view.focus();
        });
    };
    self.getImageInfo = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const state = view.state;
            const { from, to } = state.selection;
            const imageType = ctx.get(mCore.schemaCtx).nodes.image;

            const imageSrc = document.getElementById("imageSrc");
            const imageAlt = document.getElementById("imageAlt");
            const imageTitle = document.getElementById("imageTitle");
            const imageWidth = document.getElementById("imageWidth");

            imageSrc.value = '';
            imageTitle.value = '';
            imageAlt.value = '';
            imageWidth.value = '';

            state.doc.nodesBetween(from, to, (node, pos) => {
                if (node.type === imageType) {
                    const src = node.attrs.src || '';
                    const alt = node.attrs.alt || '';
                    const title = node.attrs.title || '';
                    const width = node.attrs.width || '';

                    imageSrc.value = src;
                    imageAlt.value = alt;
                    imageTitle.value = title;
                    imageWidth.value = width;
                    if (imageSrc.value !== '') {
                        document.getElementById("addImage").disabled = false;
                    }
                }
            });
        });
    };
    self.image = function() {
        var imageSrc = document.getElementById("imageSrc");
        var imageTitle = document.getElementById("imageTitle");
        var imageAlt = document.getElementById("imageAlt");
        var imageWidth = document.getElementById("imageWidth");
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const state = view.state;
            const { from, to } = state.selection;
            const imageType = ctx.get(mCore.schemaCtx).nodes.image;

            var hasImage = false;

            state.doc.nodesBetween(from, to, (node) => {
                if (node.type === imageType) {
                    hasImage = true;
                }
            });

            if (hasImage) {
                mUtils.callCommand(extendedUpdateImageCommand.key, {src: imageSrc.value, title: imageTitle.value, alt: imageAlt.value, width: imageWidth.value})(ctx);
            } else {
                mUtils.callCommand(extendedInsertImageCommand.key, {src: imageSrc.value, title: imageTitle.value, alt: imageAlt.value, width: imageWidth.value})(ctx);
            }
            $('.modal').modal('hide');
            imageSrc.value = '';
            imageTitle.value = '';
            imageAlt.value = '';
            imageWidth.value = '';
            view.focus();
        });
    };
    self.changeImage = function() {
        var imageWidth = document.getElementById("imageWidth");
        var imageLink = document.getElementById("imageLink");
        mEdit.action((ctx) => {
            mUtils.callCommand(extendedUpdateImageCommand.key, {width: imageWidth.value, link: imageLink.value})(ctx);
        });
    };
    self.italic = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            mUtils.callCommand(mCommonmark.toggleEmphasisCommand.key)(ctx);
        });
    };
    self.quote = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mCommonmark.wrapInBlockquoteCommand.key)(ctx);
        });
    };
    self.code = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mCommonmark.createCodeBlockCommand.key)(ctx);
        });
    };
    self.listNumbered = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mCommonmark.wrapInOrderedListCommand.key)(ctx);
        });
    };
    self.listBulleted = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mCommonmark.wrapInBulletListCommand.key)(ctx);
        });
    };
    self.head = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            mUtils.callCommand(mCommonmark.wrapInHeadingCommand.key, headNum)(ctx);
            headNum === 6 ? headNum = 1 : headNum =  headNum + 1;
        });
    };

    self.horizontal = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mCommonmark.insertHrCommand.key)(ctx);
        });
    };

    self.underline = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(toggleUnderlineCommand.key)(ctx);
        });
    };

    self.mokujimacro = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const state = view.state;
            const parser = ctx.get(mCore.parserCtx);

            const nodes = view.state.doc.content.content;

            const mokuji = nodes
                .filter(node => node.type.name === 'heading' && node.content && node.content.content[0])
                .map(node => {
                    const headingText = node.content.content[0].text;
                    const headingId = node.attrs.id;
                    const headingLevel = node.attrs.level;

                    const listPrefix = '* '.repeat(headingLevel);
                    return listPrefix + '[' + headingText + ']' + '(#' + headingId + ')';
                });

            const markdownText = mokuji.join('\n');
            const listNode = parser(markdownText);
            var pos = state.selection.from;
            var tr = state.tr;
            tr.insert(pos, listNode.content);
            view.dispatch(tr);
            view.focus();
        });
    };

    self.color = ko.observable('#000000');
    self.colortext = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            var state = view.state;
            var ranges = state.selection.ranges;
            var colortextMarkExists = ranges.some(r => {
                if (r.$from.pos === 1 && r.$to.pos === 1) {
                    return state.doc.rangeHasMark(r.$from.pos, r.$to.pos + 1, colortextSchema.type(ctx));
                }
                return state.doc.rangeHasMark(r.$from.pos - 1, r.$to.pos, colortextSchema.type(ctx));
            });

            if (colortextMarkExists) {
                if (self.color() !== '#000000') {
                    mUtils.callCommand(toggleColortextCommand.key, self.color())(ctx);
                }
            }
            return mUtils.callCommand(toggleColortextCommand.key, self.color())(ctx);
        });
    };

    self.strikethrough = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mGfm.toggleStrikethroughCommand.key)(ctx);
        });
    };

    self.table = function() {
        var cssArrow = document.getElementById("arrowDropDown").style.display;
        if(cssArrow === ''){
            document.getElementById("tableMenu").style.display = "";

        } else {
            mEdit.action((ctx) => {
                const view = ctx.get(mCore.editorViewCtx);
                view.focus();
                return mUtils.callCommand(mGfm.insertTableCommand.key)(ctx);
            });
        }
    };

    self.addColumnBef = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mGfm.addColBeforeCommand.key)(ctx);
        });
    };

    self.addColumnAft = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mGfm.addColAfterCommand.key)(ctx);
        });
    };

    self.addRowBef = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mGfm.addRowBeforeCommand.key)(ctx);
        });
    };

    self.addRowAft = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mGfm.addRowAfterCommand.key)(ctx);
        });
    };

    self.deleteSelectedCell = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            return mUtils.callCommand(mGfm.deleteSelectedCellsCommand.key)(ctx);
        });
    };

    self.deleteTable = function() {
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            view.focus();
            mUtils.callCommand(mGfm.selectTableCommand.key)(ctx);
            mUtils.callCommand(mGfm.deleteSelectedCellsCommand.key)(ctx);
        });
    };

    var addLink = document.querySelector('#addLink');
    addLink.onclick = self.link.bind(self);
    var addImage = document.querySelector('#addImage');
    addImage.onclick = self.image.bind(self);

    document.addEventListener('mousedown', (event) => {
        if (!(event.target.closest('.tableWrapper')) && !(event.target.closest('#tableBtn'))) {
            document.getElementById("arrowDropDown").style.display = "none";
        }
        if (!(event.target.closest('.table-dropdown-item')) && !(event.target.closest('#tableBtn'))) {
            document.getElementById("tableMenu").style.display = "none";
        }
    });

    document.addEventListener('click', (event) => {
        if (event.target.closest('#mEditor')) {
            mEdit.action((ctx) => {
                const view = ctx.get(mCore.editorViewCtx);
                view.focus();
            });
        }
        if (event.target.closest('.tableWrapper')) {
            document.getElementById("arrowDropDown").style.display = "";
        }
    });

    self.editMode = function() {
      if(self.canEdit) {
        readonly = false;
        document.getElementById("mMenuBar").style.display = "";
        document.getElementById("editWysiwyg").style.display = "none";
        document.getElementById("mEditorFooter").style.display = "";
        const milkdownDivs = document.getElementById("mEditor").querySelectorAll('div.milkdown');
        if (milkdownDivs.length === 0) {
            var request = $.ajax({
                url: self.contentURL
            });
            var rawContent = '';
            request.done(function (resp) {
                if (resp.wiki_content){
                    rawContent = resp.wiki_content;
                }
                mEdit = createMEditor(mEdit, self, rawContent);
            });
        }
        self.viewVersion('preview');
      }
    };

    self.editModeOff = function() {
        readonly = true;
        document.getElementById("mMenuBar").style.display = "none";
        document.getElementById("mEditorFooter").style.display = "none";
        document.getElementById("editWysiwyg").style.display = "";
    };

    self.submitMText = function() {
        var toMarkdown = '';
        mEdit.action((ctx) => {
            const view = ctx.get(mCore.editorViewCtx);
            const serializer = ctx.get(mCore.serializerCtx);
            toMarkdown = serializer(view.state.doc);
        });
        var pageUrl = window.contextVars.wiki.urls.page;
        $.ajax({
            url:pageUrl,
            type:'POST',
            data: JSON.stringify({markdown: toMarkdown}),
            contentType: 'application/json; charset=utf-8',
        }).done(function (resp) {
            const reloadUrl = (location.href).replace(location.search, '');
            window.location.assign(reloadUrl);
        }).fail(function(xhr) {
            var resp = JSON.parse(xhr.responseText);
            var message = resp.message;
            alert(message);
        });
    };
    self.imageSrcInput = ko.observable('');
    self.imageWidthInput = ko.observable('');
    self.canAddImage = ko.observable(false);
    self.showSizeError = ko.observable(false);

    self.validateInputs = function () {
        const width = self.imageWidthInput().trim();

        const sizePattern = /^(\d+|\d+%)$/;

        const isValidSrc = document.getElementById("imageSrc").value !== '';
        const isValidSize = width === '' || sizePattern.test(width);

        self.showSizeError(!isValidSize && width !== '');
        document.getElementById("addImage").disabled = !(isValidSrc && isValidSize);
    };

    self.imageSrcInput.subscribe(self.validateInputs);
    self.imageWidthInput.subscribe(self.validateInputs);
    self.validateInputs();
}

/**
 * If the 'Wiki images' folder does not exist for the current node, createFolder generates the request to create it
 */
function createFolder() {
    return $.ajax({
        url: wikiCtx.waterbutlerURL + 'v1/resources/' + wikiCtx.node.id + '/providers/osfstorage/?name=' + encodeURI(imageFolder) + '&kind=folder',
        type: 'PUT',
        beforeSend: $osf.setXHRAuthorization,
    });
}

/**
 * Checks to see whether there is already a 'Wiki images' folder for the current node
 *
 * If the folder doesn't exist, it attempts to create the folder
 *
 * @return {*} The folder's path attribute if it exists/was created
 */
function getOrCreateWikiImagesFolder() {
    var folderUrl = wikiCtx.apiV2Prefix + 'nodes/' + wikiCtx.node.id + '/files/osfstorage/?filter[kind]=folder&fields[file]=name,path&filter[name]=' + encodeURI(imageFolder);
    return $.ajax({
        url: folderUrl,
        type: 'GET',
        beforeSend: $osf.setXHRAuthorization,
        dataType: 'json'
    }).then(function(response) {
        if (response.data.length > 0) {
            for (var i = 0, folder; (folder = response.data[i]); i++) {

                var name = folder.attributes.name;
                if (name === imageFolder) {
                    return folder.attributes.path;
                }
            }
        }
        if (response.data.length === 0) {
            return createFolder().then(function(response) {
                return response.data.attributes.path;
            });
        }
    });
}

async function uplaodDnDFiles(files, path, fileNames) {
    var multiple = files.length > 1;
	var info = {};
    var infos = [];
    var name;
    var fileBaseUrl = (window.contextVars.wiki.urls.base).replace('wiki', 'files');
    if (path) {
        $.each(files, function (i, file) {
            var newName = null;
            if (fileNames.indexOf(file.name) !== -1) {
                newName = autoIncrementFileName(file.name, fileNames);
            }
            name = newName ? newName : file.name;
            var waterbutlerURL = wikiCtx.waterbutlerURL + 'v1/resources/' + wikiCtx.node.id + '/providers/osfstorage' + encodeURI(path) + '?name=' + encodeURIComponent(name) + '&type=file';
            $osf.trackClick('wiki', 'dropped-image', wikiCtx.node.id);
            promises.push(
                $.ajax({
                    url: waterbutlerURL,
                    type: 'PUT',
                    processData: false,
                    contentType: false,
                    beforeSend: $osf.setXHRAuthorization,
                    data: file,
                }).done(function (response) {
                    var ext = getExtension(file.name);
                    if(validImgExtensions.includes(ext)){
                        info = {name: response.data.attributes.name, path: response.data.attributes.path, url: response.data.links.download + '?mode=render'};
                        infos.push(info);
                    }else {
                        info = {name: response.data.attributes.name, path: response.data.attributes.path, url: fileBaseUrl};
                        infos.push(info);
                    }
                }).fail(function (response) {
                    notUploaded(response, false);
                })
            );
        });
        return $.when.apply(null, promises).then(function () {
            return infos;
        });
    } else {
        notUploaded(null, multiple);
    }
}

async function getFileUrl(infos) {
    var multiple = infos.length > 1;
    if (infos.length !== 0) {
        $.each(infos, function (i, info) {
            var fileUrl = wikiCtx.apiV2Prefix + 'files' + info.path;
            promises.push(
                $.ajax({
                    url: fileUrl,
                    type: 'GET',
                    beforeSend: $osf.setXHRAuthorization,
                    dataType: 'json'
                }).done(function (response) {
                    var ext = getExtension(info.name);
                    if(!(validImgExtensions.includes(ext))){
                        info.url = response.data.links.html;
                    }
                }).fail(function (response) {
                    notUploaded(response, false);
                })
            );
        });
        return $.when.apply(null, promises).then(function () {
            return infos;
        });
    } else {
        notUploaded(null, multiple);
    }
}

function autoIncrementFileName(name, nameList) {
    var num = 1;
    var newName;
    var ext = getExtension(name);
    var baseName = name.replace('.' + ext, '');

    rename:
    while (true) {
        for (var i = 0; i < nameList.length; i++) {
            newName = baseName + '(' + num + ').' + ext;
            if (nameList[i] === newName) {
                num += 1;
                newName = baseName + '(' + num + ').' + ext;
                continue rename;
            }
        }
        break;
    }
    return newName;
}

function getExtension(filename) {
    return /(?:\.([^.]+))?$/.exec(filename)[1];
}

async function localFileHandler(files) {
    var multiple = files.length > 1;
    var fileNames = [];
    var path;
    var info;
    var renderInfo;
    path = await getOrCreateWikiImagesFolder().fail(function(response) {
        notUploaded(response, multiple);
    });
    fileNames = await $.ajax({
    // Check to makes sure we don't overwrite a file with the same name.
        url: wikiCtx.waterbutlerURL + 'v1/resources/' + wikiCtx.node.id + '/providers/osfstorage' + encodeURI(path) + '?meta=',
        beforeSend: $osf.setXHRAuthorization,
    }).then(function(response) {
        return response.data.map(function(file) {
            return file.attributes.name;
        });
    }).fail(function (response) {
        notUploaded(response, false);
    });

    info = await uplaodDnDFiles(files, path, fileNames);
    renderInfo = await getFileUrl(info);
    return renderInfo;
}

function notUploaded(response, multiple) {
    var files = multiple ? 'Files' : 'File';
    if (response.status === 403) {
        $osf.growl('Error', 'File not uploaded. You do not have permission to upload files to' +
            ' this project.', 'danger');
    } else {
        $osf.growl('Error', files + ' not uploaded. Please refresh the page and try ' +
            'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
            'if the problem persists.', 'danger');
    }
}

var WikiPageMilkdown = function(selector, options) {
    var self = this;
    self.options = $.extend({}, defaultOptions, options);

    this.viewModel = new ViewModel(self.options);
    $osf.applyBindings(self.viewModel, selector);
    // Set up the event listener for the dropdown
    $('#viewVersionSelect').change(function() {
        if ($(this).val() === 'preview') {
            var request = $.ajax({
                url: self.viewModel.contentURL
            });
            var rawContent = '';
            request.done(function (resp) {
                if (resp.wiki_content){
                    rawContent = resp.wiki_content;
                }
                mEdit = createMEditor(mEdit, self.viewModel, rawContent);
            });
        }
    });
};

export default WikiPageMilkdown;
