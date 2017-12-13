var S3CompatUserConfig = require('./s3compatUserConfig.js').S3CompatUserConfig;

// Endpoint for S3 Compatible Storage user settings
var url = '/api/v1/settings/s3compat/accounts/';

var s3compatUserConfig = new S3CompatUserConfig('#s3compatAddonScope', url);
