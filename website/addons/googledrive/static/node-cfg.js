'use strict';

var AddonNodeConfig = require('addonNodeConfig').AddonNodeConfig;

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new AddonNodeConfig('googledrive', '#googledriveScope', url,
'#googledriveGrid');
