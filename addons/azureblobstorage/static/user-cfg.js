var AzureBlobStorageUserConfig = require('./azureblobstorageUserConfig.js').AzureBlobStorageUserConfig;

// Endpoint for S3 user settings
var url = '/api/v1/settings/azureblobstorage/accounts/';

var azureblobstorageUserConfig = new AzureBlobStorageUserConfig('#azureblobstorageAddonScope', url);
