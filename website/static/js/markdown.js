var hljs = require('highlight.js');
require('highlight-css');
var markdown = require('markdown-it')('commonmark', {
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

module.exports = markdown;