var S3CompatB3UserConfig = require('./s3compatb3UserConfig.js').S3CompatB3UserConfig;

// Endpoint for S3 Compatible Storage user settings
var url = '/api/v1/settings/s3compatb3/accounts/';

var s3compatb3UserConfig = new S3CompatB3UserConfig('#s3compatb3AddonScope', url);
