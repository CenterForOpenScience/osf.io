'use strict';
var hljs = require('highlight.js');
require('highlight-css');
var MarkdownIt = require('markdown-it');

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var insDel = require('markdown-it-ins-del');
var pymarkdownList = require('js/markdown-it-pymarkdown-lists');

var highlighter = function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(lang, str).value;
            } catch (__) {}
        }

        try {
            return hljs.highlightAuto(str).value;
        } catch (__) {}

        return ''; // use external default escaping
    };

/**
 * Apply .table class (from Bootstrap) to all tables
 */
var bootstrapTable = function(md) {
    md.renderer.rules.table_open = function() { return '<table class="table">'; };
};

var oldMarkdownList = function(md) {
    md.block.ruler.after('hr', 'pyMarkdownList', pymarkdownList);
};

var WATERBUTLER_REGEX = new RegExp(window.contextVars.waterbutlerURL + 'v1\/resources\/[a-zA-Z0-9]{1,}\/providers\/[a-z0-9]{1,}\/');

var viewOnlyImage = function(md) {
    var defaultRenderer = md.renderer.rules.image;
    md.renderer.rules.image = function (tokens, idx, options, env, self) {
        var token = tokens[idx];
        var imageLink = token.attrs[token.attrIndex('src')][1];
        if (imageLink.match(WATERBUTLER_REGEX) && $osf.urlParams().view_only) {
            token = tokens[idx];
            imageLink = token.attrs[token.attrIndex('src')][1];
            token.attrs[token.attrIndex('src')][1] = imageLink + '&view_only=' + $osf.urlParams().view_only;
            tokens[idx] = token;
        }
        return defaultRenderer(tokens, idx, options, env, self);
    };
};

var mfrURL = window.contextVars.node.urls.mfr;
var osfURL = window.contextVars.osfURL;

var getMfrUrl = function (guid) {
    var mfrLink = mfrURL + 'render?url='+ osfURL + guid + '/download/?action=download%26mode=render';
    if ($osf.urlParams().view_only) {
        mfrLink += '%26view_only=' + $osf.urlParams().view_only;
    }
    return mfrLink;
};

var mfrId = 0;

// Full markdown renderer for views / wiki pages / pauses between typing
var markdown = new MarkdownIt('commonmark', {
    highlight: highlighter,
    linkify: true
    }).use(require('@centerforopenscience/markdown-it-atrules'), {
        type: 'osf',
        pattern: /^http(?:s?):\/\/(?:www\.)?[a-zA-Z0-9 .:]{1,}\/render\?url=http(?:s?):\/\/[a-zA-Z0-9 .:]{1,}\/([a-zA-Z0-9]{1,})\/\?action=download|(^[a-zA-Z0-9]{1,}$)/,
        format: function(assetID) {
             var id = '__markdown-it-atrules-' + mfrId++;
             return '<div id="' + id + '" class="mfr mfr-file"></div>' +
                 '<script>$(document).ready(function () {new mfr.Render("' + id + '", "' + getMfrUrl(assetID) + '");    }); </script>';
        }
    })
    .use(require('markdown-it-video'))
    .use(require('@centerforopenscience/markdown-it-toc'))
    .use(require('markdown-it-sanitizer'))
    .use(require('markdown-it-imsize'))
    .use(viewOnlyImage)
    .use(insDel)
    .enable('table')
    .enable('linkify')
    .use(bootstrapTable)
    .disable('strikethrough');


// Fast markdown renderer for active editing to prevent slow loading/rendering tasks
var markdownQuick = new MarkdownIt('commonmark', { linkify: true })
    .use(require('markdown-it-sanitizer'))
    .use(require('markdown-it-imsize'))
    .use(viewOnlyImage)
    .disable('link')
    .disable('image')
    .use(insDel)
    .enable('table')
    .enable('linkify')
    .use(bootstrapTable)
    .disable('strikethrough');

// Markdown renderer for older wikis rendered before switch date
var markdownOld = new MarkdownIt('commonmark', { linkify: true})
    .use(require('markdown-it-sanitizer'))
    .use(require('markdown-it-imsize'))
    .use(insDel)
    .enable('table')
    .enable('linkify')
    .use(bootstrapTable)
    .use(oldMarkdownList)
    .disable('strikethrough');

module.exports = {
    full: markdown,
    quick: markdownQuick,
    old: markdownOld
};
