var $osf = require('js/osfHelpers');
var S3ViewModel = require('./s3UserConfig.js').S3ViewModel;

// Endpoint for S3 user settings
var url = '/api/v1/settings/s3/accounts/';

var s3ViewModel = new S3ViewModel(url);
$osf.applyBindings(s3ViewModel, '#s3AddonScope');

// Load initial S3 data
s3ViewModel.fetch();
