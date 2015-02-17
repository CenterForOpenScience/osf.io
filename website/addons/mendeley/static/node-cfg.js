var MendeleyNodeConfig = require('./mendeleyNodeConfig.js');

var url = window.contextVars.node.urls.api + 'mendeley/settings/';
new MendeleyNodeConfig('#mendeleyScope', url, '#mendeleyGrid');
