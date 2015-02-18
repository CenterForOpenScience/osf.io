var MendeleyNodeConfig = require('./mendeleyNodeConfig.js');
require('./node-cfg.css');

var url = window.contextVars.node.urls.api + 'mendeley/settings/';
new MendeleyNodeConfig('#mendeleyScope', url, '#mendeleyGrid');
