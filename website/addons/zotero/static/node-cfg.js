var CitationsNodeConfig = require('citationsNodeConfig');
require('./node-cfg.css');

var url = window.contextVars.node.urls.api + 'zotero/settings/';
new CitationsNodeConfig('Zotero', '#zoteroScope', url, '#zoteroGrid');
