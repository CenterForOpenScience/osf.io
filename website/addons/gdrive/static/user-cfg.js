var GdriveUserConfig = require('./gdriveUserConfig.js');

// Endpoint for dropbox user settings
var url = '/api/v1/settings/gdrive';
// Start up the Dropbox Config manager
new GdriveUserConfig('#driveAddonScope', url);
