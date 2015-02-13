var $ = require('jquery');
var Raven = require('raven-js');
var $osf = require('osfHelpers');
require('bootstrap-editable');
var md = require('markdown');

require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');

var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');

var url = window.contextVars.wiki.urls.content;
var metadata = window.contextVars.wiki.metadata;
ShareJSDoc('.wiki', url, metadata);

var ctx = window.contextVars.wiki;  // mako context variables
var versions = {};  // Cache fetched wiki versions
var currentWiki = '';

// Render the raw markdown of the wiki
if (!ctx.usePythonRender) {
    var markdownElement = $('#markdown-it-render');
    var request = $.ajax({
        url: ctx.urls.content
    });
    request.done(function(resp) {
        var rawText = resp.wiki_content || '*No wiki content*';
        currentWiki = md.render(rawText);
        markdownElement.html(currentWiki);
    });
}

// Version selection
var previewElement = $('#viewPreview');
var versionElement = $('#viewVersion');

// Cache versions already displayed on page

// Change content of wiki on version select
$('#viewSelect').change(function() {
    var preview = (this.value === 'preview');
    previewElement.toggle(preview);
    versionElement.toggle(!preview);
    if (!preview) {
        var version = this.value;
        if (version === 'current') {
            versionElement.html(currentWiki);
        } else if (version in versions) {
            versionElement.html(versions[version]);
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
                versionElement.html(wikiText);
                versions[version] = wikiText;
            });
        }
    }
});

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