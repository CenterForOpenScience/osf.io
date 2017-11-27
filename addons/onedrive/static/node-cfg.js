'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'onedrive/config/';
new OauthAddonNodeConfig('Microsoft OneDrive', '#onedriveScope', url, '#onedriveGrid');
