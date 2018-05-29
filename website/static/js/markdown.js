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
    return mfrURL + 'render?url='+ osfURL + guid + '/?action=download%26mode=render'
};

// Full markdown renderer for views / wiki pages / pauses between typing
var markdown = new MarkdownIt('commonmark', {
    highlight: highlighter,
    linkify: true
    }).use(require('markdown-it-mfr'), {
        type: 'osf',
        pattern: /^http(?:s?):\/\/(?:www\.)?[a-zA-Z0-9 .:]{1,}\/render\?url=http(?:s?):\/\/[a-zA-Z0-9 .:]{1,}\/([a-zA-Z0-9]{5})\/\?action=download|(^[a-zA-Z0-9]{5}$)/,
        format(assetID) {
          var id = '__markdown-it-mfr-' + (new Date()).getTime();
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

// Disable backspace sending you back a page in firefox. This is just a usability fix because users
// tend to click out of the text box while it loads MFR embeds, then press backspace, believing the
// cursor is still active.
// https://stackoverflow.com/questions/1495219/how-can-i-prevent-the-backspace-key-from-navigating-back
$(document).unbind('keydown').bind('keydown', function (event) {
    if (event.keyCode === 8) {
        var doPrevent = true;
        var types = ['text', 'password', 'file', 'search', 'email', 'number', 'date', 'color', 'datetime', 'datetime-local', 'month', 'range', 'search', 'tel', 'time', 'url', 'week'];
        var d = $(event.srcElement || event.target);
        var disabled = d.prop('readonly') || d.prop('disabled');
        if (!disabled) {
            if (d[0].isContentEditable) {
                doPrevent = false;
            } else if (d.is('input')) {
                var type = d.attr('type');
                if (type) {
                    type = type.toLowerCase();
                }
                if (types.indexOf(type) > -1) {
                    doPrevent = false;
                }
            } else if (d.is('textarea')) {
                doPrevent = false;
            }
        }
        if (doPrevent) {
            event.preventDefault();
            return false;
        }
    }
});