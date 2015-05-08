'use strict';

require('./dropbox.css');
var AddonNodeConfig = require('js/addonNodeConfig').AddonNodeConfig;

var url = window.contextVars.node.urls.api + 'dropbox/config/';
new AddonNodeConfig('Dropbox', '#dropboxScope', url, '#dropboxGrid');
