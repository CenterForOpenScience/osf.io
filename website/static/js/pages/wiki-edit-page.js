require('ace-noconflict');
require('ace-mode-markdown');

var WikiEditor = require('addons/wiki/static/WikiEditor.js');
var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');

// Generate gravatar URL
var CryptoJS = require("crypto-js");
var email = window.contextVars.wiki.email;
var baseGravatarUrl = '//secure.gravatar.com/avatar/';
var hash = CryptoJS.MD5(email.toLowerCase().trim());
var params = '?d=identicon&size=32';
window.contextVars.wiki.metadata.userGravatar = baseGravatarUrl + hash + params;

var url = window.contextVars.wiki.urls.content;
var metadata = window.contextVars.wiki.metadata;

// Toggle tooltips
$(function () {
    $('[data-toggle="tooltip"]').tooltip();
});

var wikiEditor = new WikiEditor('.wiki', url);
ShareJSDoc(wikiEditor.viewModel, url, metadata);