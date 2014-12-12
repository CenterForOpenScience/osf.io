var GdriveNodeConfig = require('./gdriveNodeConfig.js');

var url = window.contextVars.node.urls.api + 'gdrive/config/';
new GdriveNodeConfig('#driveAddonScope', url, '#myGdriveGrid');
