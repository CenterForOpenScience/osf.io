'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'googledriveinstitutions/config/';
new OauthAddonNodeConfig('Google Drive in G Suite / Google Workspace', '#googledriveinstitutionsScope', url, '#googledriveinstitutionsGrid');
