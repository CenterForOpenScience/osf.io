var GithubUserConfig = require('./githubUserConfig.js');

// Endpoint for github user settings
var url = '/api/v1/settings/github/';
// Start up the Dropbox Config manager
new GithubUserConfig('#githubAddonScope', url);
