'use strict';

require('./box.css')
var BoxNodeConfig = require('./boxNodeConfig').BoxNodeConfig;

var url = window.contextVars.node.urls.api + 'box/settings/';
new BoxNodeConfig('Box', '#boxScope', url, '#boxGrid');
