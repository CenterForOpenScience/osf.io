'use strict';

var CitationsNodeConfig = require('js/citationsNodeConfig').CitationsNodeConfig;

var url = window.contextVars.node.urls.api + 'zotero/settings/';
new CitationsNodeConfig('Zotero', '#zoteroScope', url, '#zoteroGrid');
