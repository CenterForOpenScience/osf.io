var WEKONodeConfig = require('./wekoNodeConfig.js');

var url = window.contextVars.node.urls.api + 'weko/settings/';
new WEKONodeConfig('#wekoScope', url);
