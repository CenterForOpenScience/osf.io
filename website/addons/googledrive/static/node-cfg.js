var GoogleDriveNodeConfig = require('./googleDriveNodeConfig.js').GoogleDriveNodeConfig;

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new GoogleDriveNodeConfig('#googleDriveAddonScope', url, '#myGoogleDriveGrid');
