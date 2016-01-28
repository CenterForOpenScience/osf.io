var S3UserConfig = require('./s3UserConfig.js').S3UserConfig;

// Endpoint for S3 user settings
var url = '/api/v1/settings/s3/accounts/';

var s3UserConfig = new S3UserConfig('#s3AddonScope', url);
