'use strict';

var OauthAddonNodeConfig = require('js/oauthAddonNodeConfig').OauthAddonNodeConfig;

var url = window.contextVars.node.urls.api + 's3/settings/';
new OauthAddonNodeConfig('Amazon S3', '#s3Scope', url, '#s3Grid');
