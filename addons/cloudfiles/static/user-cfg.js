var CloudFilesUserConfig = require('./cloudfilesUserConfig.js').CloudFilesUserConfig;

// Endpoint for cloudfiles user settings
var url = '/api/v1/settings/cloudfiles/accounts/';

var CloudFilesConfig = new CloudFilesUserConfig('#cloudfilesAddonScope', url);
