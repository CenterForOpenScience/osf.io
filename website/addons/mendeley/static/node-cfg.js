var CitationsNodeConfig = require('citationsNodeConfig');
require('./node-cfg.css');

var url = window.contextVars.node.urls.api + 'mendeley/settings/';
new CitationsNodeConfig('Mendeley', '#mendeleyScope', url, '#mendeleyGrid');
