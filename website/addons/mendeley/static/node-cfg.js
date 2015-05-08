'use strict';

var CitationsNodeConfig = require('js/citationsNodeConfig').CitationsNodeConfig;
require('./node-cfg.css');

var url = window.contextVars.node.urls.api + 'mendeley/settings/';
new CitationsNodeConfig('Mendeley', '#mendeleyScope', url, '#mendeleyGrid');
