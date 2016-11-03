var OwnCloudNodeConfig = require('./owncloudNodeConfig.js');

var url = window.contextVars.node.urls.api + 'owncloud/settings/';
new OwnCloudNodeConfig('#owncloudScope', url);
