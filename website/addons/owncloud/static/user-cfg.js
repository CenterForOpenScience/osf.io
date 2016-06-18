var $osf = require('js/osfHelpers');
var OwnCloudViewModel = require('./owncloudUserConfig.js').OwnCloudViewModel;

var url = '/api/v1/settings/owncloud/';

var owncloudViewModel = new OwnCloudViewModel(url);
$osf.applyBindings(owncloudViewModel, '#owncloudAddonScope');

owncloudViewModel.fetch();
