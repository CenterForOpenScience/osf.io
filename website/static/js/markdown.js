'use strict';
var hljs = require('highlight.js');
require('highlight-css');
var MarkdownIt = require('markdown-it');

var $ = require('jquery');
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
var mfrURL = window.contextVars.mfrURL;
var osfURL = window.contextVars.osfURL;

var getMfrUrl = function (guid) {
    var mfrLink = mfrURL + 'render?url='+ osfURL + guid + '/?action=download%26mode=render';
    if (window.contextVars.node.viewOnlyLink) {
        mfrLink += '&view_only=' + window.contextVars.node.viewOnlyLink;
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
    .use(insDel)
    .enable('table')
    .enable('linkify')
    .use(bootstrapTable)
    .disable('strikethrough');


// Fast markdown renderer for active editing to prevent slow loading/rendering tasks
var markdownQuick = new MarkdownIt('commonmark', { linkify: true })
    .use(require('markdown-it-sanitizer'))
    .use(require('markdown-it-imsize'))
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
