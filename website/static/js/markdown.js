var hljs = require('highlight.js');
require('highlight-css');
var MarkdownIt = require('markdown-it')

var markdown = new MarkdownIt('commonmark', {
    highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(lang, str).value;
            } catch (__) {}
        }

        try {
            return hljs.highlightAuto(str).value;
        } catch (__) {}

        return ''; // use external default escaping
    }
})
    .use(require('markdown-it-video'))
    .use(require('markdown-it-sanitizer'));

var markdown_quick = new MarkdownIt(('commonmark'), {
     highlight: function (str, lang) {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return hljs.highlight(lang, str).value;
            } catch (__) {}
        }

        try {
            return hljs.highlightAuto(str).value;
        } catch (__) {}

        return ''; // use external default escaping
    }
})
    .use(require('markdown-it-sanitizer'))
    .disable('image');

module.exports = markdown;
module.exports = markdown_quick;