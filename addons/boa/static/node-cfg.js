var BoaNodeConfig = require('./boaNodeConfig.js');

var url = window.contextVars.node.urls.api + 'boa/settings/';
new BoaNodeConfig('#boaScope', url);
