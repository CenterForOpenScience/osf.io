'use strict';

require('./dropbox.css');
var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'dropbox/config/';
new OauthAddonNodeConfig('Dropbox', '#dropboxScope', url, '#dropboxGrid');
