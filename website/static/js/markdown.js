'use strict';
var hljs = require('highlight.js');
require('highlight-css');
var MarkdownIt = require('markdown-it');

var insDel = require('markdown-it-ins-del');

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

// Full markdown renderer for views / wiki pages / pauses between typing
var markdown = new MarkdownIt('commonmark', {
    highlight: highlighter
})
    .use(require('markdown-it-video'))
    .use(require('markdown-it-prezi'))
    .use(require('markdown-it-toc'))
    .use(require('markdown-it-sanitizer'))
    .use(insDel)
    .enable('table')
    .use(bootstrapTable)
    .disable('strikethrough');


// Fast markdown renderer for active editing to prevent slow loading/rendering tasks
var markdownQuick = new MarkdownIt(('commonmark'), { })
    .use(require('markdown-it-sanitizer'))
    .disable('link')
    .disable('image')
    .use(insDel)
    .enable('table')
    .use(bootstrapTable)
    .disable('strikethrough');

module.exports = {
    full: markdown,
    quick: markdownQuick
};
