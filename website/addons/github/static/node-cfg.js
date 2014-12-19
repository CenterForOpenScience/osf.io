var GithubNodeConfig = require('./githubNodeConfig.js');

var url = window.contextVars.node.urls.api + 'github/config/';
var submitUrl = window.contextVars.node.urls.api + 'github/settings/';
new GithubNodeConfig('#githubScope', url, submitUrl);
