'use strict';

require('./dropbox.css');
var AddonNodeConfig = require('js/addonNodeConfig');

var url = window.contextVars.node.urls.api + 'dropbox/config/';
new AddonNodeConfig('Dropbox', '#dropboxScope', url, '#dropboxGrid');
