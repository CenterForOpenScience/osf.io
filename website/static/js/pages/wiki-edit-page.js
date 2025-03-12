'use strict';

var $ = require('jquery');
var Raven = require('raven-js');
require('bootstrap-editable');
require('osf-panel');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var WikiPage = require('wikiPage');

require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');
require('../../vendor/ace-plugins/spellcheck_ace.js');

var WikiMenu = require('../wikiMenu');
var Comment = require('js/comment'); //jshint ignore:line
var $osf = require('js/osfHelpers');

var ctx = window.contextVars.wiki;  // mako context variables

var editable = (ctx.panelsUsed.indexOf('edit') !== -1);
var viewable = (ctx.panelsUsed.indexOf('view') !== -1);
var comparable = (ctx.panelsUsed.indexOf('compare') !== -1);
var menuVisible = (ctx.panelsUsed.indexOf('menu') !== -1);

var viewVersion = ctx.versionSettings.view || (editable ? 'preview' : 'current');
var compareVersion = ctx.versionSettings.compare || 'previous';

var wikiPageOptions = {
    editVisible: editable,
    viewVisible: viewable,
    compareVisible: comparable,
    menuVisible: menuVisible,
    canEdit: ctx.canEdit,
    viewVersion: viewVersion,
    compareVersion: compareVersion,
    urls: ctx.urls,
    metadata: ctx.metadata
};

var wikiPage = new WikiPage('#wikiPageContext', wikiPageOptions);


// Edit wiki page name
if (ctx.canEditPageName) {
    // Initialize editable wiki page name
    var $pageName = $('#pageName');
    $.fn.editable.defaults.mode = 'inline';
    $pageName.editable({
        type: 'text',
        send: 'always',
        url: ctx.urls.rename,
        ajaxOptions: {
            type: 'put',
            contentType: 'application/json',
            dataType: 'json'
        },
        validate: function(value) {
            if($.trim(value) === ''){
                return _('The wiki page name cannot be empty.');
            } else if(value.length > 100){
                return _('The wiki page name cannot be more than 100 characters.');
            }
        },
        params: function(params) {
            return JSON.stringify(params);
        },
        success: function(response, value) {
            window.location.href = ctx.urls.base + encodeURIComponent(value) + '/';
        },
        error: function(response) {
            var msg = response.responseJSON.message_long;
            if (msg) {
                return msg;
            } else {
                // Log unexpected error with Raven
                Raven.captureMessage(_('Error in renaming wiki'), {
                    extra: {
                        url: ctx.urls.rename,
                        responseText: response.responseText,
                        statusText: response.statusText
                    }
                });
                return _('An unexpected error occurred. Please try again.');
            }
        }
    });
}

// Apply panels
$(document).ready(function () {
    var errorMsg = $('#wikiErrorMessage');
    var grid = $('#grid');
    // Treebeard Wiki Menu
    $.ajax({
        url: ctx.urls.grid
    })
    .done(function (data) {
        new WikiMenu(data, ctx.wikiID, ctx.canEdit);
    })
    .fail(function(xhr, status, error) {
        grid.addClass('hidden');
        errorMsg.removeClass('hidden');
        errorMsg.append(_('<p>Could not retrieve wiki pages. Please reload the page. If this issue persists, ') +
            sprintf(_('please report it to %1$s') , $osf.osfSupportLink()));
        Raven.captureMessage(_('Could not GET wiki menu pages'), {
            extra: { url: ctx.urls.grid, status: status, error: error }
        });
    });

    var bodyElement = $('body');

    $('*[data-osf-panel]').osfPanel({
        buttonElement : '.switch',
        onSize : 'xs',
        'onclick' : function (event, title, buttonState, thisbtn, col) {
            // this = all the column elements; an array
            // title = Text of the button
            // buttonState = the visibility of column after click, taen from data-osf-toggle attribute,
            // thisbtn = $(this);
            // col = the $() for the column this button links to

            // Determine if any columns are visible
            var visibleColumns = this.filter(function (i, element) {
                return $(element).is(':visible');
            });

            if (visibleColumns.length === 0) {
                thisbtn.click();
                return;
            }

            bodyElement.trigger('togglePanel', [
                title.toLowerCase(),
                buttonState
            ]);
            if (typeof editor !== 'undefined') { ace.edit(editor).resize(); } // jshint ignore: line
        },
        complete : function() {
            if (typeof editor !== 'undefined') { ace.edit(editor).resize(); } // jshint ignore: line
        }
    });

    var panelToggle = $('.panel-toggle');
    var panelExpand = $('.panel-expand');
    $('.panel-collapse').on('click', function () {
        var el = $(this).closest('.panel-toggle');
        el.children('.osf-panel').addClass('hidden');
        el.children('.osf-panel').addClass('visible-xs');
        panelToggle.removeClass('col-sm-3').addClass('col-sm-1');
        panelExpand.removeClass('col-sm-9').addClass('col-sm-11');
        el.children('.panel-collapsed').removeClass('hidden');
        el.children('.panel-collapsed').removeClass('visible-xs');
        $('.wiki-nav').removeClass('hidden');

        bodyElement.trigger('toggleMenu', [false]);
    });
    $('.panel-collapsed .panel-heading').on('click', function () {
        var el = $(this).parent();
        var toggle = el.closest('.panel-toggle');
        toggle.children('.osf-panel').removeClass('hidden');
        toggle.children('.osf-panel').removeClass('visible-xs');
        el.addClass('hidden');
        panelToggle.removeClass('col-sm-1').addClass('col-sm-3');
        panelExpand.removeClass('col-sm-11').addClass('col-sm-9');
        $('.wiki-nav').addClass('hidden');
        bodyElement.trigger('toggleMenu', [true]);
    });

    // Tooltip
    $('[data-toggle="tooltip"]').tooltip();
});

var $comments = $('.comments');
if ($comments.length && window.contextVars.wiki.wikiID !== null) {
    var options = {
        nodeId: window.contextVars.node.id,
        nodeApiUrl: window.contextVars.node.urls.api,
        isRegistration: window.contextVars.node.isRegistration,
        page: 'wiki',
        rootId: window.contextVars.wiki.wikiID,
        fileId: null,
        canComment: window.contextVars.currentUser.canComment,
        currentUser: window.contextVars.currentUser,
        pageTitle: window.contextVars.wiki.wikiName,
        inputSelector: '.atwho-input'
    };
    Comment.init('#commentsLink', '.comment-pane', options);
}

// Disable backspace sending you back a page in firefox. This is just a usability fix because users
// tend to click out of the text box while it loads MFR embeds, then press backspace, believing the
// cursor is still active.
// https://stackoverflow.com/questions/1495219/how-can-i-prevent-the-backspace-key-from-navigating-back
$(document).unbind('keydown').bind('keydown', function (event) {
    if (event.keyCode === 8) {
        var doPrevent = true;
        var types = ['text', 'password', 'file', 'search', 'email', 'number', 'date', 'color', 'datetime', 'datetime-local', 'month', 'range', 'search', 'tel', 'time', 'url', 'week'];
        var d = $(event.srcElement || event.target);
        var disabled = d.prop('readonly') || d.prop('disabled');
        if (!disabled) {
            if (d[0].isContentEditable) {
                doPrevent = false;
            } else if (d.is('input')) {
                var type = d.attr('type');
                if (type) {
                    type = type.toLowerCase();
                }
                if (types.indexOf(type) > -1) {
                    doPrevent = false;
                }
            } else if (d.is('textarea')) {
                doPrevent = false;
            }
        }
        if (doPrevent) {
            event.preventDefault();
            return false;
        }
    }
});

//nishi
function loadFinished(){
    // URLのアンカー（#以降の部分）を取得
    var urlHash = location.hash;
    console.log('Test1' + urlHash);
    // URLにアンカーが存在する場合
    if(urlHash){
        window.location.hash = urlHash
    }
}

window.onload = loadFinished;
//nishi
