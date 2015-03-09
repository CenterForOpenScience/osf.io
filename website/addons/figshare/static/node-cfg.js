var FigshareNodeConfig = require('./figshareNodeConfig.js');

var url = window.contextVars.node.urls.api + 'figshare/config/';
new FigshareNodeConfig('#figshareScope', url, '#figshareGrid');
