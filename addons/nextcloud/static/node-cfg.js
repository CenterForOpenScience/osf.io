var NextcloudNodeConfig = require('./nextcloudNodeConfig.js');

var url = window.contextVars.node.urls.api + 'nextcloud/settings/';
new NextcloudNodeConfig('#nextcloudScope', url);
