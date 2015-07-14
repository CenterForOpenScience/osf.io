var githubNodeConfig = require('./githubNodeConfig').githubNodeConfig;

var url = window.contextVars.node.urls.api + 'github/settings/';
new githubNodeConfig('#githubScope', url);