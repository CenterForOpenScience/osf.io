require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');

var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');

var url = window.contextVars.wiki.urls.content;
var metadata = window.contextVars.wiki.metadata;

// Toggle tooltips
$(function () {
    $('[data-toggle="tooltip"]').tooltip();
});

ShareJSDoc('.wiki', url, metadata);