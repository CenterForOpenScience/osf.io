'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new OauthAddonNodeConfig('Google Drive', '#googledriveScope', url, '#googledriveGrid');
