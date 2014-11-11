var DropboxNodeConfig = require('./dropboxNodeConfig.js');

var url = window.contextVars.node.urls.api + 'dropbox/config/';
new DropboxNodeConfig('#dropboxScope', url, '#myDropboxGrid');
