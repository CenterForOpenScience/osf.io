var FedoraNodeConfig = require('./FedoraNodeConfig.js');

var url = window.contextVars.node.urls.api + 'fedora/settings/';
new FedoraNodeConfig('#fedoraScope', url);
