'use strict';

var $ = require('jquery');
var AddonHelper = require('js/addonHelper');

$(window.contextVars.gitlabSettingsSelector).on('submit', AddonHelper.onSubmitSettings);

// Endpoint for GitLab user settings
var url = '/api/v1/settings/gitlab/';
var $osf = require('js/osfHelpers');
var GitLabViewModel = require('./gitlabNodeConfig.js').GitLabViewModel;
var gitlabViewModel = new GitLabViewModel(url);

// Load initial GitLab data
gitlabViewModel.fetch();
$osf.applyBindings(gitlabViewModel, '#gitlabScope');
