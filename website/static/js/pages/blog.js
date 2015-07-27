'use strict';
var ko = require('knockout');
var hljs = require('highlight.js');
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
var md = new MarkdownIt('commonmark', {
    highlight: highlighter
})
    .use(require('markdown-it-video'))
    .use(require('markdown-it-toc'))
    .use(require('markdown-it-sanitizer'))
    .use(insDel);

console.log(md.render(process.argv[2]));
