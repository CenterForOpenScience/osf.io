'use strict';

require('./fedora.css');
var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'fedora/config/';
new OauthAddonNodeConfig('Fedora', '#fedoraScope', url, '#fedoraGrid');
