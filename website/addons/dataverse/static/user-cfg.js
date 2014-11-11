var DataverseUserConfig = require('./dataverseUserConfig.js');

// Endpoint for Dataverse user settings
var url = '/api/v1/settings/dataverse/';
// Start up the DataverseConfig manager
DataverseUserConfig('#dataverseAddonScope', url);
