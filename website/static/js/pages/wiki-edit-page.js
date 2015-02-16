var $ = require('jquery');
var Raven = require('raven-js');
var $osf = require('osfHelpers');
require('bootstrap-editable');
require('osf-panel');
var md = require('markdown');

var ctx = window.contextVars.wiki;  // mako context variables

var selectElement = $('#viewSelect');
var previewElement = $('#viewPreview');
var versionElement = $('#viewVersion');
var markdownElement = $('#markdown-it-render');

// Collaborative editor
if (ctx.canEdit) {
    require('ace-noconflict');
    require('ace-mode-markdown');
    require('ace-ext-language_tools');
    require('addons/wiki/static/ace-markdown-snippets.js');

    var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');
    ShareJSDoc('.wiki', ctx.urls.draft, ctx.metadata);
}

var versions = {};  // Cache fetched wiki versions
var currentWiki = '';

// Render the raw markdown of the wiki
if (!ctx.usePythonRender) {
    var request = $.ajax({
        url: ctx.urls.content
    });
    request.done(function(resp) {
        var rawText = resp.wiki_content || '*No wiki content*';
        currentWiki = md.render(rawText);
        markdownElement.html(currentWiki);
    });
}

// Wiki version selection
selectElement.change(function() {
    var preview = (this.value === 'preview');
    previewElement.toggle(preview);
    versionElement.toggle(!preview);
    if (!preview) {
        var version = this.value;
        if (version === 'current') {
            markdownElement.html(currentWiki);
        } else if (version in versions) {
            markdownElement.html(versions[version]);
        } else {
            var request = $.ajax({
                url: ctx.urls.content + this.value
            });
            request.done(function(resp) {
                var wikiText;
                if (resp.wiki_rendered) {
                    wikiText = resp.wiki_rendered;
                } else {
                    var rawText = resp.wiki_content;
                    wikiText = md.render(rawText);
                }
                markdownElement.html(wikiText);
                versions[version] = wikiText;
            });
        }
    }
});

// Default view will vary based on permissions/url. Trigger manually once
selectElement.trigger('change');

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
                return 'The wiki page name cannot be empty.';
            } else if(value.length > 100){
                return 'The wiki page name cannot be more than 100 characters.';
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
                Raven.captureMessage('Error in renaming wiki', {
                    url: ctx.urls.rename,
                    responseText: response.responseText,
                    statusText: response.statusText
                });
                return 'An unexpected error occurred. Please try again.';
            }
        }
    });
}

// Apply panels
$(document).ready(function () {
    $('*[data-osf-panel]').osfPanel({
        buttonElement : '.switch',
        onSize : 'md',
        'onclick' : function () { editor.resize(); }
    });

    var panelToggle = $('.panel-toggle'),
        panelExpand = $('.panel-expand');
    $('.panel-collapse').on('click', function () {
        var el = $(this).closest('.panel-toggle');
        el.children('.wiki-panel.hidden-xs').hide();
        panelToggle.removeClass('col-sm-3').addClass('col-sm-1');
        panelExpand.removeClass('col-sm-9').addClass('col-sm-11');
        el.children('.panel-collapsed').show();
    });
    $('.panel-collapsed').on('click', function () {
        var el = $(this),
            toggle = el.closest('.panel-toggle');
        toggle.children('.wiki-panel').show();
        el.hide();
        panelToggle.removeClass('col-sm-1').addClass('col-sm-3');
        panelExpand.removeClass('col-sm-11').addClass('col-sm-9');
    });
});