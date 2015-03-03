var CitationsNodeConfig = require('../../../static/js/citationsNodeConfig.js');
require('./node-cfg.css');

var url = window.contextVars.node.urls.api + 'mendeley/settings/';
new CitationsNodeConfig('Mendeley', '#mendeleyScope', url, '#mendeleyGrid');
