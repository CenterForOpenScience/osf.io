var DropboxUserConfig = require('./dropboxUserConfig.js');

// Endpoint for dropbox user settings
var url = '/api/v1/settings/dropbox/';
// Start up the Dropbox Config manager
new DropboxUserConfig('#dropboxAddonScope', url);
