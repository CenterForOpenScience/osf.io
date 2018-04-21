var $osf = require('js/osfHelpers');
var NextcloudUserConfig = require('./nextcloudUserConfig.js').NextcloudUserConfig;

var url = '/api/v1/settings/nextcloud/accounts/';
var NextcloudUserConfig = new NextcloudUserConfig('#nextcloudAddonScope',url);
NextcloudUserConfig.viewModel.fetch();
