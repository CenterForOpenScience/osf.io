var $osf = require('js/osfHelpers');
var OwnCloudUserConfig = require('./owncloudUserConfig.js').OwnCloudUserConfig;

var url = '/api/v1/settings/owncloud/accounts/';
var ownCloudUserConfig = new OwnCloudUserConfig('#owncloudAddonScope',url);
ownCloudUserConfig.viewModel.fetch();
