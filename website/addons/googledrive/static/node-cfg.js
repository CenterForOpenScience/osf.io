var AddonNodeConfig = require('addonNodeConfig');

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new AddonNodeConfig('Google Drive', '#googledriveScope', url, '#googledriveGrid');
