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

// Full markdown renderer for views / wiki pages / pauses between typing
var markdown = new MarkdownIt('commonmark', {
    highlight: highlighter
})
    .use(require('markdown-it-video'))
    .use(require('markdown-it-toc'))
    .use(require('markdown-it-sanitizer'))
    .use(insDel)
    .disable('strikethrough');


// Fast markdown renderer for active editing to prevent slow loading/rendering tasks
var markdownQuick = new MarkdownIt(('commonmark'), { })
    .use(require('markdown-it-sanitizer'))
    .disable('link')
    .disable('image')
    .use(insDel)
    .disable('strikethrough');

module.exports = {
    full: markdown,
    quick: markdownQuick
};