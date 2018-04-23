var $ = require('jquery');
var $osf = require('js/osfHelpers');
var OwnCloudUserConfig = require('./owncloudRdmConfig.js').OwnCloudUserConfig;

var institutionId = $('#owncloudAddonScope').data('institution-id');
//var url = '/api/v1/settings/owncloud/accounts/';
var url = '/addons/api/v1/settings/owncloud/' + institutionId + '/accounts/';
var ownCloudUserConfig = new OwnCloudUserConfig('#owncloudAddonScope', url, institutionId);
ownCloudUserConfig.viewModel.fetch();
