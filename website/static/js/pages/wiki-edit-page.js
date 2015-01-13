var WikiEditor = require('addons/wiki/static/WikiEditor.js');
var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js')

var url = window.contextVars.wiki.urls.content;
var metadata = window.contextVars.wiki.metadata;

// Generate gravatar URL
var baseGravatarUrl = 'http://secure.gravatar.com/avatar/';
var hash = CryptoJS.MD5('${user_name}'.toLowerCase().trim());
var params = '?d=identicon&size=32';
metadata.gravatarUrl = baseGravatarUrl + hash + params;

var wikiEditor = new WikiEditor('.wiki', url);
ShareJSDoc(wikiEditor.viewModel, url, metadata);
