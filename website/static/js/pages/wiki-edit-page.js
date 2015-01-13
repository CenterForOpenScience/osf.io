var WikiEditor = require('addons/wiki/static/WikiEditor.js');
var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js')

var url = window.contextVars.wiki.urls.content;
var metadata = window.contextVars.wiki.metadata;

var wikiEditor = new WikiEditor('.wiki', url);
ShareJSDoc(wikiEditor.viewModel, url, metadata);
