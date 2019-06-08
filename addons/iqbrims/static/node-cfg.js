'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'iqbrims/config/';
new OauthAddonNodeConfig('IQB-RIMS', '#iqbrimsScope', url, '#iqbrimsGrid');
