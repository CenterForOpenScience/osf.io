'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'dmptool/settings/';
new OauthAddonNodeConfig('DMPTool', '#dmptoolScope', url, '#dmptoolGrid');
