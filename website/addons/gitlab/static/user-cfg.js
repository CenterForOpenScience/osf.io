var $osf = require('js/osfHelpers');
var GitLabViewModel = require('./gitlabUserConfig.js').GitLabViewModel;

// Endpoint for GitLab user settings
var url = '/api/v1/settings/gitlab/';

var gitlabViewModel = new GitLabViewModel(url);
$osf.applyBindings(gitlabViewModel, '#gitlabAddonScope');

// Load initial GitLab data
gitlabViewModel.fetch();
