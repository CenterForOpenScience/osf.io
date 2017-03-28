var DmptoolNodeConfig = require('./dmptoolNodeConfig.js');

var url = window.contextVars.node.urls.api + 'dmptool/settings/';
new DmptoolNodeConfig('#dmptoolScope', url);
