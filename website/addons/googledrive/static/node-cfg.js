var GoogleDriveNodeConfig = require('./googleDriveNodeConfig.js');

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new GoogleDriveNodeConfig('#googleDriveAddonScope', url, '#myGoogleDriveGrid');
