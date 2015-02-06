require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');

var WikiEditor = require('addons/wiki/static/WikiEditor.js');
var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');

var url = window.contextVars.wiki.urls.content;
var metadata = window.contextVars.wiki.metadata;

// Toggle tooltips
$(function () {
    $('[data-toggle="tooltip"]').tooltip();
});

var wikiEditor = new WikiEditor('.wiki', url);
ShareJSDoc(wikiEditor.viewModel, url, metadata);