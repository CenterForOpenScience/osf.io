var ZoteroNodeConfig = require('./zoteroNodeConfig.js');
require('./node-cfg.css');

var url = window.contextVars.node.urls.api + 'zotero/settings/';
new ZoteroNodeConfig('#zoteroScope', url, '#zoteroGrid');;
