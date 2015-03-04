var BoxNodeConfig = require('./boxNodeConfig.js');

var url = window.contextVars.node.urls.api + 'box/config/';
new BoxNodeConfig('#boxScope', url, '#myBoxGrid');
