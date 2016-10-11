'use strict';

require('./onedrive.css');
var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'onedrive/settings/';
new OauthAddonNodeConfig('Onedrive', '#onedriveScope', url, '#onedriveGrid');
