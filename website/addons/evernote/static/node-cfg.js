'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 'evernote/settings/';
new OauthAddonNodeConfig('Evernote', '#evernoteScope', url, '#evernoteGrid');
