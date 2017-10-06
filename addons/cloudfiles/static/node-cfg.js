var CloudFilesNodeConfig = require('./cloudfilesNodeConfig.js');

var url = window.contextVars.node.urls.api + 'cloudfiles/settings/';
new CloudFilesNodeConfig('#cloudfilesScope', url);
