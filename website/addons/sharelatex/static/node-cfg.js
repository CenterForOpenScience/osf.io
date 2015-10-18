'use strict';

var $ = require('jquery');
var AddonHelper = require('js/addonHelper');
var ShareLatexNodeConfig = require('./sharelatexNodeConfig').ShareLatexNodeConfig;

var ctx = window.contextVars;  // mako context variables

var sharelatexSettings = {
    url: ctx.node.urls.api + 'sharelatex/settings/',
};

new ShareLatexNodeConfig('#sharelatexScope', sharelatexSettings);
