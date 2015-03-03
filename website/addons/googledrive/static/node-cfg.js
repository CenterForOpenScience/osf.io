/*var GoogleDriveNodeConfig = require('./googleDriveNodeConfig.js');

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new GoogleDriveNodeConfig('#googleDriveAddonScope', url, '#myGoogleDriveGrid');
*/
var AddonNodeConfig = require('../../../static/js/addonNodeConfig');

var url = window.contextVars.node.urls.api + 'googledrive/config/';
new AddonNodeConfig('Google Drive', '#googledriveScope', url, '#googledriveGrid');
