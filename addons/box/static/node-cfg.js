'use strict';

require('./box.css');
var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'box/settings/';
new OauthAddonNodeConfig('Box', '#boxScope', url, '#boxGrid');
