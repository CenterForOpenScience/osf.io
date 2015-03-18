var GoogleDriveNodeConfig = require('./googleDriveNodeConfig.js').GoogleDriveNodeConfig;

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new GoogleDriveNodeConfig('googledrive', '#googleDriveAddonScope', url, '#myGoogleDriveGrid');
