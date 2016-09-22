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

var oldMarkdownList = function(md) {

    md.block.ruler.after('list', 'pymark_list', function replace(state) {

        var this_list_markup;
        var list_type;

        if (state.tokens.length > 0) {
            if (state.tokens.slice(-2)[0].type === 'ordered_list_open') {
                list_type = 'ordered';
            }

        }
        for (var i = 0; i < state.tokens.length; i++) {
            if (list_type === 'ordered') {
                if (state.tokens[i].markup === '*') {
                    state.tokens[i].markup = '1';
                }
            }
        }

    });
};

// Full markdown renderer for views / wiki pages / pauses between typing
var markdown = new MarkdownIt('commonmark', {
    highlight: highlighter
})
    .use(require('markdown-it-video'))
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

// Markdown renderer for older wikis rendered before switch date
var markdownOld = new MarkdownIt(('commonmark'), { html: true })
    .use(require('markdown-it-sanitizer'))
    .use(insDel)
    .enable('table')
    .use(bootstrapTable)
    .use(oldMarkdownList)
    .disable('strikethrough');

module.exports = {
    full: markdown,
    quick: markdownQuick,
    old: markdownOld
};
