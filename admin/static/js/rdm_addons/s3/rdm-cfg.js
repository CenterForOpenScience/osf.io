var S3UserConfig = require('./s3RdmConfig.js').S3UserConfig;

// Endpoint for S3 user settings
var institutionId = $('#s3AddonScope').data('institution-id');
//var url = '/api/v1/settings/s3/accounts/';
var url = '/addons/api/v1/settings/s3/' + institutionId + '/accounts/';

var s3UserConfig = new S3UserConfig('#s3AddonScope', url, institutionId);
